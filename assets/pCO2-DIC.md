Dissolved Inorganic Carbon (DIC) represents the sum of all inorganic carbon species dissolved in water.  
It is a key variable of the carbonate system and directly linked to pH, alkalinity, and gas exchange with atmospheric CO₂.




---

### Dissolved Inorganic Carbon (DIC)

DIC is computed as the sum of all dissolved inorganic carbon species:

$$
\mathrm{DIC} = [\mathrm{CO_2(aq)}] + [\mathrm{HCO_3^-}] + [\mathrm{CO_3^{2-}}]
$$

---

### Total Alkality (TA)
The total alkalinity can be composed of different conjugate base of any weak acid.

The model used here assumes **pure carbonate alkalinity**, meaning that alkalinity arises only from the carbonate system and not from organic acids or other weak acid–base pairs.

- The system contains only CO₂(aq), HCO₃⁻, CO₃²⁻, H⁺, and OH⁻  
- Total alkalinity is defined exclusively by carbonate species  
- Organic alkalinity is not present 
- other inorganic alkalinity is not present (borate alkalinity, phosphate alkalinity etc.)
- Speciation follows the equilibrium constants of carbonic acid  
  $K_1$ and $K_2$
- In our model case the alkalinity can be described by:  

  $$
  \mathrm{TA} = [\mathrm{HCO_3^-}] + 2[\mathrm{CO_3^{2-}}] - [\mathrm{H^+}] + [\mathrm{OH^-}]
  $$

---

### DIC–pCO₂ Relationship

1. **Gas dissolution (Henry’s Law)**  

   $$
   [\mathrm{CO_2(aq)}] = K_0 \, p\mathrm{CO_2}
   $$

2. **Carbonate equilibria**  

   $$
   K_1 = \frac{[\mathrm{H^+}][\mathrm{HCO_3^-}]}{[\mathrm{CO_2(aq)}]}
   $$

   $$
   K_2 = \frac{[\mathrm{H^+}][\mathrm{CO_3^{2-}}]}{[\mathrm{HCO_3^-}]}
   $$

3. **Alkalinity constraint**  

   $$
   \mathrm{TA} = [\mathrm{HCO_3^-}] + 2[\mathrm{CO_3^{2-}}] - [\mathrm{H^+}] + [\mathrm{OH^-}]
   $$

These relationships define how DIC varies with atmospheric pCO₂ at a given total alkalinity.
