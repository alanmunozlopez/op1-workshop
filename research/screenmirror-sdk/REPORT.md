# Viabilidad de ScreenMirror en Hundekraft

Fecha: 2026-11-10. Investigación en `research/screenmirror-sdk`.

**Resultado: el port es viable, pero el SDK público actual no basta para reproducir nuestro ScreenMirror completo.** Hay autoinicio, memoria y trabajo fuera de audio. Faltan un acceso de captura final con contrato explícito y una salida SysEx adecuada. La vía mantenible sería añadir esos servicios al núcleo Kennel y después entregar el mirror como `.knl`. No se ha construido ni instalado ese port.

## Material comprobado

- Fork: https://github.com/alanmunozlopez/op1-workshop
- Upstream: https://github.com/Hundekraft/op1-workshop
- Commit base: `96114bdd233b81f3a1ed49f7b74069096aa6071a`.
- `release.json`: Hundekraft **3.2.3**, release `a909f630a6e723fc`, compilador Blackfin GCC 13.3.0.
- SDK realmente inspeccionado: `source/hundekraft-3.2.3-source.tar.gz`, SHA-256 **`7a74872170bcb812750b65989184ef81fd06ab1fbb6c9066091a613162137033`**, comprobado contra su `.sha256` y fijado en `bootstrap_sdk.py`.
- La guía enlaza todavía un paquete 3.2; el README principal menciona 3.0.1. La evaluación usa el archivo **3.2.3 que coincide con el manifiesto de esta revisión**, no esas etiquetas anteriores.
- Fuente extraída bajo `.work/sdk/hundekraft-3.2.3-source/ext/kennel/`; las rutas siguientes son relativas a ese directorio.

La fuente del firmware, headers, tabla de exportaciones y las implementaciones reales se contrastaron entre sí. No se dedujo que un servicio existe solo porque aparezca en una guía.

## Comprobaciones

| Necesidad | Resultado | Evidencia del SDK 3.2.3 |
|---|---|---|
| Plugin externo independiente | Sí: `.knl`, tipo `feature` | `op1_feature.h`; `tools/kennel/pack.py`; `docs/plugin-format.md` |
| Arrancar sin navegar por el instrumento | Sí, para una feature instalada y habilitada | `kn_features.c:182`, registro en boot; `kn_core.c:94`, `OP1_EV_BOOT_DONE` |
| Compresión/transporte fuera de audio | Sí, trabajo corto en `OP1_EV_SERVICE` | `op1_feature.h:64`; `kn_core.c:121` |
| Memoria propia para snapshots | Sí: `op1_alloc`, cero al reservar, sin free, NULL si no cabe | `op1_feature.h:146`; `kn_exports.c:99`; `kn_core.c:177`; `kn_boot.c:504` |
| Observar el dibujo de la interfaz | Parcial: `overlay(raster, screen)` en Gfx | `op1_feature.h:120` |
| Leer píxeles mediante API pública de captura | No se encontró un getter/copy exportado con geometría y vida útil | `op1_plugin.h:352` da un raster opaco; `kn_exports.c` no ofrece el servicio de captura requerido |
| Capturar la composición final | El overlay no alcanza las capas finales del núcleo | `kn_core.c:258`: base → overlays → texto modal → toast |
| SysEx de nuestro protocolo por API pública | No: el helper actual admite solo 1–3 bytes y no empaqueta SysEx | `op1_feature.h:148`; `kn_core.c:166`; `kn_exports.c:101` |
| USB capaz de SysEx | Sí: el propio actualizador lo utiliza | `devupd/du_fw.c:679`, `static send_sysex`; `du.h:11`, hasta 256 bytes |
| Recibir heartbeat SysEx del visor | No mediante `midi_raw` actual | `kn_midi.c:163`: no entrega CIN 4/5/6/7 al callback |

Los ficheros `kn_*` de esta tabla están en `synth_sdk/kennel/`; los headers están en `synth_sdk/`. `devupd` también está bajo `synth_sdk/`.

## Pantalla: alcance real del overlay

El callback público recibe un raster en el hilo gráfico después del dibujo base. Las páginas normales de ajustes se añaden a la tabla de pantallas (`kn_pages.c:116`), y el aviso de confirmación USB reemplaza una entrada de esa tabla (`devupd/du_fw.c:599`). Por tanto, su dibujo debería llegar al overlay; esta es una inferencia del código y todavía no una prueba física.

Sin embargo, el texto de entrada modal y los avisos se dibujan **después de todos los overlays**. Elegir una prioridad alta solo cambia el orden entre features. No convierte el overlay en un callback de la imagen final.

Existe evidencia de lectura de píxeles dentro de la fuente:

- `plugins/randomiser/rn_draw.c:39` interpreta una estructura nativa con puntero RGB565, ancho, stride y alto.
- `synth_sdk/kennel/kn_artcache.c:82` copia píxeles con controles de metadatos, pero esa ruta está limitada al panel por defecto y vuelve al dibujo habitual para otros paneles.

Esto permite investigar una captura parcial ligada a la versión. **No demuestra una API genérica soportada para los tres paneles**, ni autoriza retener el raster para leerlo más tarde desde main. Esa lectura podría competir con el hilo gráfico o captar un buffer que ya cambió. La orientación, recorte y geometría tienen que comprobarse; no se trasladan automáticamente los offsets de OPUS.

## USB: por qué dividir el SysEx en trozos no resuelve el problema

La prueba ejecuta los cuerpos C reales de `op1_midi_send` y `kn_midi_raw_packet`, con sus hashes fijados. Solo sustituye el encolador USB y el observador de entrada por mocks. Se compila con ASan y UBSan y no abre ningún puerto MIDI.

Resultados observados:

1. Un mensaje de nota de tres bytes produce el CIN MIDI esperado.
2. Una trama SysEx completa de 92 bytes es rechazada por longitud.
3. Un inicio `F0 7D 53` de tres bytes se clasifica como **CIN 3** (system common), cuando un SysEx continuado necesita **CIN 4**.
4. Una continuación de solo bytes de datos es rechazada por no empezar con un byte de estado.
5. El callback público de entrada no recibe los paquetes SysEx que sí puede procesar el actualizador privado.

`op1_midi_send` devuelve cero después de invocar un encolador de firmware que retorna void. Ese valor no es un ACK del Mac ni una garantía de que había sitio en el ring. Tampoco ofrece consulta pública de USB configurado o presión de cola.

**La limitación demostrada es de API, no de capacidad física del USB.** El núcleo ya tiene empaquetado SysEx correcto para el actualizador, pero ese helper es estático y no forma parte de la tabla de exportaciones.

Un plugin nativo podría intentar llamar directamente a una dirección privada del firmware que aparece en la fuente. El packer no vuelve imposible ese atajo. Sería otra integración profunda, dependiente de versión y pendiente de auditar, con dudas de colas, convivencia con el actualizador y cobertura gráfica. No se ha usado ni se presenta como una solución soportada por el SDK.

## Ruta recomendada para el port

Estas son propuestas de contrato; **no son funciones existentes del SDK**:

1. Un observador de la imagen final, después de las capas de texto/toast y antes de entregar el framebuffer. Debe describir formato, dimensiones, orientación, stride y cuánto dura la validez del puntero. El plugin solo copiaría a sus snapshots dentro del callback.
2. Una salida SysEx acotada desde main, con empaquetado correcto y resultado de cola explícito. Debe coordinarse con el actualizador USB, reservar margen para MIDI musical y evitar esperas en audio o Gfx. Para nuestro protocolo, un mensaje de hasta 92 bytes y envío incremental bastaría como punto de partida, pendiente de medir.
3. Mantener compresión, regiones, selección de captura reciente y reconstrucción del Mac de nuestro proyecto, adaptando la captura y la capa de transporte a esos servicios.

La recepción SysEx solo sería necesaria para un futuro handshake/pausa cuando no hay visor. **No es un requisito para el primer streaming automático** y permanece fuera de esta prueba.

La extensión del núcleo requiere revisión, compilación y validación del firmware Hundekraft correspondiente. Un `.knl` que importase esos servicios no funcionaría en un núcleo anterior que no los exporte. No se ha parcheado el núcleo en esta investigación ni se ha preparado una imagen para flashear.

## Artefactos y reproducción

```sh
# Verificar y extraer el paquete público ya incluido en este repo:
python3 research/screenmirror-sdk/bootstrap_sdk.py

# Si Blackfin GCC/binutils están en PATH:
sh research/screenmirror-sdk/build-probe.sh

# Alternativa: señalar la carpeta que contiene bfin-elf-gcc y bfin-elf-ld:
BFIN_BIN="/ruta/al/toolchain/bin" sh research/screenmirror-sdk/build-probe.sh
```

La compilación comprobada usa `bfin-elf-gcc (GCC) 13.3.0`. El packer oficial crea `artifacts/sm_sdk_probe.knl`: **544 bytes**, imports `_op1_alloc` y `_op1_midi_send`, callbacks de registro/servicio/overlay y ninguna reclamación de controles. Su wrapper de enlace MIDI no es invocado por los callbacks. No lee framebuffer ni transmite datos.

**Ese `.knl` es únicamente una prueba de compilación/enlace; no es ScreenMirror y no debe instalarse para recuperar la pantalla.**

La prueba de contrato USB está en `tests/test_usb_contract.py`. El script extrae las funciones del SDK verificado y elimina la compilación temporal al terminar. No distribuye copias modificadas de esas implementaciones.

Los archivos de investigación usan GPL-3.0-or-later; la fuente del SDK mantiene sus LICENSE/NOTICE y el permiso adicional relativo al OP-1. No se han incorporado firmware de TE, capturas privadas, audio, claves ni datos del instrumento.

## Límites de esta comprobación

Se han verificado fuente, exportaciones, compilación Blackfin y contratos C simulados. **No se ha probado carga del `.knl` en hardware, ni un framebuffer real, velocidad de USB, CPU, audio o estabilidad.** Esta investigación no conecta con el instrumento ni cambia su instalación. El proyecto funcional de OPUS permanece intacto.

La confirmación con T1 puede prepararse desde el navegador, pero eso no valida por sí solo una migración a ciegas. Conviene tener el port completo y una ruta de recuperación comprobada antes de cambiar el firmware del instrumento con pantalla averiada.
