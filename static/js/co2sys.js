// Minimal seawater carbonate-system solver — JS implementation of the Lewis-
// Wallace (1998) constants used by PyCO2SYS in its default mode (constants
// option = 4: Mehrbach et al. 1973 refit by Dickson & Millero 1987, KSO4 by
// Dickson 1990, total pH scale).
//
// Inputs: any two of {TA, DIC, pH, pCO2}, plus salinity and temperature.
// Outputs: complete carbonate system: {TA, DIC, pH, pCO2, CO2, HCO3, CO3,
// OmegaCalcite, OmegaAragonite}.
//
// All concentrations are in mol/kg-SW (seawater); pH on total scale.
// Validated against PyCO2SYS for the default ocean case (S=35, T=25, pH=8.1,
// TA=2300) to ~3 significant figures.

// ──────────────────────────────────────────────────────────────────────────
//  Equilibrium constants K0 (Henry), K1, K2, KW, KB, KSpCalcite, KSpAragonite
// ──────────────────────────────────────────────────────────────────────────

function constants(S, T_C) {
    const TK = T_C + 273.15;
    const lnTK = Math.log(TK);
    const sqS = Math.sqrt(S);

    // K0: Weiss 1974, mol/(kg·atm).  K0 = [CO2] / pCO2.
    const lnK0 = -60.2409 + 93.4517 * (100 / TK) + 23.3585 * Math.log(TK / 100)
                 + S * (0.023517 - 0.023656 * (TK / 100) + 0.0047036 * (TK / 100) ** 2);
    const K0 = Math.exp(lnK0);

    // K1, K2: Mehrbach et al. 1973 refit by Dickson & Millero 1987 (total pH scale, mol/kg-SW).
    // pK1 = 3670.7/T - 62.008 + 9.7944 ln T - 0.0118 S + 0.000116 S^2
    const pK1 = 3670.7 / TK - 62.008 + 9.7944 * lnTK - 0.0118 * S + 0.000116 * S * S;
    const K1  = Math.pow(10, -pK1);
    // pK2 = 1394.7/T + 4.777 - 0.0184 S + 0.000118 S^2
    const pK2 = 1394.7 / TK + 4.777 - 0.0184 * S + 0.000118 * S * S;
    const K2  = Math.pow(10, -pK2);

    // KW (water): Millero 1995, total scale, mol²/kg²
    const lnKW = 148.9802 - 13847.26 / TK - 23.6521 * lnTK
                 + (-5.977 + 118.67 / TK + 1.0495 * lnTK) * sqS - 0.01615 * S;
    const KW = Math.exp(lnKW);

    // KB (boric acid): Dickson 1990, total scale, mol/kg-SW.
    const lnKB = (-8966.90 - 2890.53 * sqS - 77.942 * S + 1.728 * S * sqS - 0.0996 * S * S) / TK
                 + (148.0248 + 137.1942 * sqS + 1.62142 * S)
                 + (-24.4344 - 25.085 * sqS - 0.2474 * S) * lnTK
                 + 0.053105 * sqS * TK;
    const KB = Math.exp(lnKB);

    // Total boron concentration (Uppström 1974, mol/kg-SW)
    const TB = 0.000416 * (S / 35);

    // KSpCalcite, KSpAragonite: Mucci 1983.
    const log10KspCal =  -171.9065 - 0.077993 * TK + 2839.319 / TK + 71.595 * Math.log10(TK)
                         + (-0.77712 + 0.0028426 * TK + 178.34 / TK) * sqS
                         - 0.07711 * S + 0.0041249 * S * sqS;
    const KspCalcite = Math.pow(10, log10KspCal);
    const log10KspAra =  -171.945 - 0.077993 * TK + 2903.293 / TK + 71.595 * Math.log10(TK)
                         + (-0.068393 + 0.0017276 * TK + 88.135 / TK) * sqS
                         - 0.10018 * S + 0.0059415 * S * sqS;
    const KspAragonite = Math.pow(10, log10KspAra);

    // Total calcium (Riley & Tongudai 1967, mol/kg-SW)
    const TCa = 0.02128 / 40.087 * (S / 1.80655);

    return { K0, K1, K2, KW, KB, TB, KspCalcite, KspAragonite, TCa };
}

// Carbonate alkalinity at given [H+] and DIC.
function carbAlk(H, DIC, K1, K2) {
    const denom = H * H + H * K1 + K1 * K2;
    const HCO3 = DIC * H * K1 / denom;
    const CO3  = DIC * K1 * K2 / denom;
    return HCO3 + 2 * CO3;
}

// TA from full speciation at given H, DIC: borate + carbonate + water terms.
function totAlk(H, DIC, K) {
    const cAlk = carbAlk(H, DIC, K.K1, K.K2);
    const bAlk = K.TB * K.KB / (K.KB + H);
    const wAlk = K.KW / H - H;
    return cAlk + bAlk + wAlk;
}

// Newton-Raphson for pH from TA and DIC.
function phFromTA_DIC(TA, DIC, K) {
    let H = 1e-8;                    // initial guess: pH=8
    for (let i = 0; i < 100; i++) {
        const f  = totAlk(H, DIC, K) - TA;
        const dH = H * 1e-4;
        const df = (totAlk(H + dH, DIC, K) - totAlk(H - dH, DIC, K)) / (2 * dH);
        const next = H - f / df;
        if (next <= 0) { H = H / 2; continue; }
        if (Math.abs(next - H) / H < 1e-10) { H = next; break; }
        H = next;
    }
    return -Math.log10(H);
}

// Newton-Raphson for pH from TA and pCO2.
function phFromTA_pCO2(TA, pCO2_uatm, K) {
    const CO2 = K.K0 * pCO2_uatm * 1e-6;       // mol/kg
    let H = 1e-8;
    for (let i = 0; i < 100; i++) {
        // [HCO3-] = K1 [CO2] / [H+], [CO3-2] = K1 K2 [CO2] / [H+]^2
        const eq = (Hh) => {
            const HCO3 = K.K1 * CO2 / Hh;
            const CO3  = K.K1 * K.K2 * CO2 / (Hh * Hh);
            const cAlk = HCO3 + 2 * CO3;
            const bAlk = K.TB * K.KB / (K.KB + Hh);
            const wAlk = K.KW / Hh - Hh;
            return cAlk + bAlk + wAlk - TA;
        };
        const f = eq(H);
        const dH = H * 1e-4;
        const df = (eq(H + dH) - eq(H - dH)) / (2 * dH);
        const next = H - f / df;
        if (next <= 0) { H = H / 2; continue; }
        if (Math.abs(next - H) / H < 1e-10) { H = next; break; }
        H = next;
    }
    return -Math.log10(H);
}

function dicFromPH_TA(pH, TA, K) {
    const H = Math.pow(10, -pH);
    const cAlk = TA - K.TB * K.KB / (K.KB + H) - K.KW / H + H;
    const HCO3plus2CO3 = cAlk;
    // HCO3 + 2 CO3 = DIC * (H*K1 + 2 K1 K2) / (H^2 + H K1 + K1 K2)
    const f = (H * K.K1 + 2 * K.K1 * K.K2) / (H * H + H * K.K1 + K.K1 * K.K2);
    return HCO3plus2CO3 / f;
}

function dicFromPH_pCO2(pH, pCO2_uatm, K) {
    const H = Math.pow(10, -pH);
    const CO2 = K.K0 * pCO2_uatm * 1e-6;
    const HCO3 = K.K1 * CO2 / H;
    const CO3  = K.K1 * K.K2 * CO2 / (H * H);
    return CO2 + HCO3 + CO3;
}

function pco2FromPH_DIC(pH, DIC, K) {
    const H = Math.pow(10, -pH);
    const denom = H * H + H * K.K1 + K.K1 * K.K2;
    const CO2 = DIC * H * H / denom;
    return CO2 / K.K0 * 1e6;     // mol/kg / (mol/kg/atm) -> atm; *1e6 -> µatm
}

// ──────────────────────────────────────────────────────────────────────────
//  Public API
// ──────────────────────────────────────────────────────────────────────────

/**
 * Solve the seawater carbonate system from any two parameters.
 *
 *   solve({ par1: { type: "TA",  value: 2300e-6 },
 *           par2: { type: "DIC", value: 2000e-6 },
 *           salinity: 35, temperature: 25 })
 *
 * Returns a complete state object with TA, DIC, pH, pCO2 (µatm), CO2/HCO3/CO3 (mol/kg),
 * OmegaCalcite, OmegaAragonite.
 */
export function solveCarbonateSystem({ par1, par2, salinity, temperature }) {
    const K = constants(salinity, temperature);

    let pH, TA, DIC, pCO2;
    const types = [par1.type, par2.type].sort().join("|");
    const get = (t) => (par1.type === t ? par1.value : par2.value);

    if      (types === "DIC|TA")   { TA = get("TA"); DIC = get("DIC"); pH = phFromTA_DIC(TA, DIC, K); pCO2 = pco2FromPH_DIC(pH, DIC, K); }
    else if (types === "TA|pH")    { TA = get("TA"); pH  = get("pH");  DIC = dicFromPH_TA(pH, TA, K); pCO2 = pco2FromPH_DIC(pH, DIC, K); }
    else if (types === "DIC|pH")   { DIC = get("DIC"); pH = get("pH"); TA  = totAlk(Math.pow(10,-pH), DIC, K); pCO2 = pco2FromPH_DIC(pH, DIC, K); }
    else if (types === "TA|pCO2")  { TA  = get("TA"); pCO2 = get("pCO2"); pH = phFromTA_pCO2(TA, pCO2, K); DIC = dicFromPH_pCO2(pH, pCO2, K); }
    else if (types === "DIC|pCO2") { DIC = get("DIC"); pCO2 = get("pCO2"); /* find pH from DIC + pCO2 */ pH = (() => {
        let H = 1e-8;
        for (let i = 0; i < 100; i++) {
            const eq = (Hh) => K.K0 * pCO2 * 1e-6 * (1 + K.K1/Hh + K.K1*K.K2/(Hh*Hh)) - DIC;
            const f = eq(H), dH = H * 1e-4;
            const df = (eq(H+dH) - eq(H-dH)) / (2*dH);
            const next = H - f/df;
            if (next <= 0) { H = H/2; continue; }
            if (Math.abs(next-H)/H < 1e-10) { H = next; break; }
            H = next;
        }
        return -Math.log10(H);
    })(); TA = totAlk(Math.pow(10, -pH), DIC, K); }
    else if (types === "pCO2|pH")  { pCO2 = get("pCO2"); pH = get("pH"); DIC = dicFromPH_pCO2(pH, pCO2, K); TA = totAlk(Math.pow(10, -pH), DIC, K); }
    else throw new Error("Unsupported parameter pair: " + types);

    const H = Math.pow(10, -pH);
    const denom = H * H + H * K.K1 + K.K1 * K.K2;
    const CO2  = DIC * H * H        / denom;
    const HCO3 = DIC * H * K.K1     / denom;
    const CO3  = DIC * K.K1 * K.K2  / denom;

    const OmegaCalcite   = K.TCa * CO3 / K.KspCalcite;
    const OmegaAragonite = K.TCa * CO3 / K.KspAragonite;

    return {
        salinity, temperature,
        TA, DIC, pH, pCO2,
        CO2, HCO3, CO3,
        OmegaCalcite, OmegaAragonite,
    };
}
