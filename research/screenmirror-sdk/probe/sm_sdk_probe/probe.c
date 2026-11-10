/* SPDX-License-Identifier: GPL-3.0-or-later
 * Compile/link feasibility probe, NOT a ScreenMirror implementation.
 * See the repository LICENSE/NOTICE for the additional OP-1 permission.
 * No control ownership, framebuffer reads, audio callback, files or USB sends
 * are performed by this feature. Do not install it to recover a display. */
#include "op1_feature.h"

static void *scratch;
static volatile uint32_t services, overlays;

static void observe_event(int id, int32_t arg)
{
    (void)arg;
    if (id == OP1_EV_REGISTER && !scratch) scratch = op1_alloc(32);
    if (id == OP1_EV_SERVICE) services++;
}

static void observe_overlay(void *raster, int32_t screen)
{
    (void)raster;
    (void)screen;
    overlays++;
}

/* Kept as non-static code so the packer verifies the real MIDI import.
 * It is not registered as a callback and no code in the feature invokes it. */
int sm_sdk_probe_link_midi(const uint8_t *message, int length)
{
    return op1_midi_send(message, length);
}

static const char *const no_claims[] = { 0 };
const op1_feature_t FEATURE_sm_sdk_probe = {
    .api = OP1_FEATURE_API,
    .priority = 65000,
    .name = "sm_sdk_probe",
    .event = observe_event,
    .overlay = observe_overlay,
    .claims = no_claims
};
