# Comprobación del SDK para ScreenMirror

El fork y la prueba se mantienen en `research/screenmirror-sdk`. Véase [REPORT.md](REPORT.md) para evidencia y límites.

**Conclusión:** el SDK de Hundekraft 3.2.3 permite una feature que arranque sola, reserve memoria y trabaje en main. La API pública no ofrece el transporte SysEx de nuestro mirror ni una captura final completa con geometría/propiedad definidas. El port es viable como trabajo de núcleo + plugin; no está listo para instalar ni equivale a renombrar el `.opmod` de OPUS.

`build-probe.sh` verifica el SDK, compila una prueba mínima con el packer oficial y ejecuta el contrato MIDI real con ASan/UBSan. No usa el instrumento. Su `.knl` es una prueba de enlace sin streaming y no debe instalarse como ScreenMirror.

No se modificaron las fuentes del núcleo, los plugins oficiales ni el proyecto funcional de OPUS.
