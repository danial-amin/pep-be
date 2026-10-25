/** Default simulation goal/context for study participants (PX / P01…). */

export const STUDY_SIMULATION_DEFAULT_GOAL =
  'To discuss how to get the households out of NSER to receive aid.';

export const STUDY_SIMULATION_DEFAULT_CONTEXT = `BISP will open a 30-day exceptional registration window in notified flood-affected districts. Households that are absent from the National Socio-Economic Registry may register at temporary desks located at union council level.

Eligibility will be confirmed by a local verification committee comprising:

a BISP field officer;
a district administration representative; and
one community representative.
Approved households will receive PKR 25,000 in two payments of PKR 12,500. The second payment will be released after post-payment verification.

Registration will require a Computerized National Identity Card. A household without a CNIC may be enrolled provisionally using a witness attestation, but payment will be held until the household’s identity is confirmed.`;

/** PX / PX1–PX6 test codes, or standard participant codes P01, P02, … */
export function shouldUseStudySimulationDefaults(code?: string | null): boolean {
  if (!code) return false;
  const c = code.trim().toUpperCase();
  return /^PX([1-6])?$/.test(c) || /^P\d{1,3}$/.test(c);
}
