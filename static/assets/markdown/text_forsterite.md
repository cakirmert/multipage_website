The functional relationship describing how forsterite dissolves as a function of pH and temperature is taken from \[1\].

The equations describing the dissolution process are taken from \[2\].


We assume:
- A spherical particle of initial radius $r_0$
- A constant dissolution rate $R$ in mol·m$^{-2}$·s$^{-1}$
- The process is surface-controlled (no diffusion limitations)
- The molar volume of the mineral is $V_m$ in m³/mol

---

### 1. Surface Area of the Sphere

$$
A(t) = 4\pi r(t)^2
$$

---

### 2. Volume of the Sphere

$$
V(t) = \frac{4}{3} \pi r(t)^3
$$

---

### 3. Number of Moles in the Sphere

Using molar volume:

$$
n(t) = \frac{V(t)}{V_m} = \frac{\frac{4}{3} \pi r(t)^3}{V_m}
$$

---

### 4. Rate of Change of Moles (Dissolution)

The dissolution removes moles from the surface at a constant rate:

$$
\frac{dn}{dt} = -R \cdot A(t) = -R \cdot 4\pi r(t)^2
$$

We also know:

$$
n(t) = \frac{4}{3} \pi \cdot \frac{r(t)^3}{V_m}
\quad \Rightarrow \quad
\frac{dn}{dt} = 4\pi r(t)^2 \cdot \frac{dr}{dt} \cdot \frac{1}{V_m}
$$

---

### 5. Equating Both Expressions

$$
4\pi r(t)^2 \cdot \frac{dr}{dt} \cdot \frac{1}{V_m} = -R \cdot 4\pi r(t)^2
$$

Cancel $4\pi r(t)^2$ from both sides:

$$
\frac{dr}{dt} = -R \cdot V_m
$$

---

### 6. Integration to Get Radius Over Time

$$
\int dr = -R \cdot V_m \cdot \int dt
\Rightarrow
r(t) = r_0 - R \cdot V_m \cdot t
$$

---

### 7. Volume Over Time

$$
V(t) = \frac{4}{3} \pi \left( r_0 - R \cdot V_m \cdot t \right)^3
$$

---

### 8. Moles Over Time

$$
n(t) = \frac{V(t)}{V_m} = \frac{4\pi}{3 V_m} \left( r_0 - R \cdot V_m \cdot t \right)^3
$$

---

### 9. Time Until Complete Dissolution

Complete dissolution occurs when $r(t)=0$:

$$
r_0 - R \cdot V_m \cdot t = 0 \Rightarrow t_{\text{dissolve}} = \frac{r_0}{R \cdot V_m}
$$

---

### Summary of Analytical Expressions

- **Radius**:
  $$
  r(t) = r_0 - R \cdot V_m \cdot t
  $$
- **Volume**:
  $$
  V(t) = \frac{4}{3} \pi \left( r(t) \right)^3
  $$
- **Moles**:
  $$
  n(t) = \frac{V(t)}{V_m}
  $$
- **Dissolution Time**:
  $$
  t_{\text{dissolve}} = \frac{r_0}{R \cdot V_m}
  $$