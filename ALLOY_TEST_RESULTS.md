# Проверка расчётов и генерации текстур · v2

Все **73 состава** вернули строгий JSON и дали PNG. Статусы расчёта: **27 `ok`**, **36 `partial`**, **10 `unsupported`**. Пять прежних сбоев сериализации и Fe–Cl теперь дают `unsupported` без свойств сплава. На десяти керамических составах предупреждения о свободных O и N отсутствуют.

- **Al₂O₃**: 3970 кг/м³, плавление 2327 K. **TiC**: 4910 кг/м³, плавление 3326 K.
- **SiC**: 3210 кг/м³, типичная температура разложения или сублимации 3281 K.
- **Fe–C**: ликвидус снижается с 1803 K при 0,1% C до 1741 K при 0,8% C. У состава Fe:93.9,C:3.4,Si:2.2,Mn:0.5 оценка ликвидуса 1471 K.
- **Латунь Cu:70,Zn:30**: жёлтый оттенок `#D5AB37` из текстурного профиля C26000.

Условия: `raw`, воздух, 298,15 K, активность кислорода 0,21. Текстуры проверены на шаблоне слитка с текущими настройками `.env`. **S** — солидус, **L** — ликвидус, **пл.** — плавление. «—» означает, что оценка недоступна или неприменима. Склонность к коррозии — эвристика для заданной среды. Гальванический риск требует отдельного контекста контакта.

## Углеродные стали

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Fe:99.9,C:0.1` | ok | steel | 115.3 | 7864 | S 1766, L 1803 | 0.63 | `#A3B1C6` | 1, 2 | — |
| `Fe:99.7,C:0.3` | ok | steel | 148.4 | 7853 | S 1742, L 1786 | 0.63 | `#A1B0C4` | 1, 2 | — |
| `Fe:99.55,C:0.45` | ok | steel | 172.4 | 7844 | S 1715, L 1773 | 0.63 | `#A0AFC3` | 1, 2 | — |
| `Fe:99.2,C:0.8` | partial | steel | — | 7825 | S 1654, L 1741 | 0.63 | `#9EAAC0` | 1, 2 | 1 |
| `Fe:98.95,C:1.05` | partial | steel | — | 7810 | S 1611, L 1718 | 0.63 | `#9DABBF` | 1, 2 | 1 |
| `Fe:99.05,C:0.2,Mn:0.6,Si:0.15` | ok | steel | 144.8 | 7847 | пл. 1794 | 0.63 | `#A2B1C5` | 2 | — |
| `Fe:98.55,C:0.45,Mn:0.75,Si:0.25` | ok | steel | 189.7 | 7826 | пл. 1796 | 0.63 | `#A0AFC3` | 2 | — |
| `Fe:98.35,C:0.6,Mn:0.85,Si:0.2` | partial | steel | — | 7820 | пл. 1798 | 0.63 | `#9FAEC2` | 2 | 1 |

## Легированные стали

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Fe:97.35,Cr:1,Mo:0.2,Mn:0.8,Si:0.25,C:0.4` | ok | steel | 219.5 | 7826 | пл. 1782 | 0.63 | `#A0B2C3` | 2 | — |
| `Fe:95.8,Ni:1.8,Cr:0.8,Mo:0.25,Mn:0.7,Si:0.25,C:0.4` | ok | steel | 228.8 | 7848 | пл. 1775 | 0.62 | `#A2B3C4` | 2 | — |
| `Fe:72.44,Cr:18,Ni:8,Mn:1,Si:0.5,C:0.06` | ok | steel | 277.3 | 7786 | пл. 1814 | 0.02 | `#A6C2CB` | 2 | — |
| `Fe:66.27,Cr:17,Ni:12,Mo:2.5,Mn:1.5,Si:0.7,C:0.03` | ok | steel | 298.9 | 7880 | пл. 1813 | 0.02 | `#A5CBCB` | 2 | — |
| `Fe:81.92,Cr:17,C:0.08,Mn:0.6,Si:0.4` | ok | steel | 239.7 | 7717 | пл. 1828 | 0.02 | `#A6BBCA` | 2 | — |
| `Fe:86.38,Cr:12.5,C:0.12,Mn:0.5,Si:0.5` | ok | steel | 235.5 | 7743 | пл. 1810 | 0.55 | `#A5B7C9` | 2 | — |
| `Fe:84.5,Cr:12,Mo:1,V:1,C:1.5` | partial | steel | — | 7703 | пл. 1739 | 0.55 | `#9EB3C0` | 2 | 1 |
| `Fe:90.8,Cr:5.2,Mo:1.3,V:0.9,Si:1,Mn:0.4,C:0.4` | ok | steel | 323.4 | 7766 | пл. 1793 | 0.62 | `#A1B5C4` | 2 | — |
| `Fe:86.8,Mn:12,C:1.2` | ok | steel | 351.6 | 7734 | пл. 1759 | 0.62 | `#9DABBF` | 2 | — |
| `Fe:81.25,W:6,Mo:5,Cr:4,V:2,C:0.85,Si:0.3,Mn:0.6` | partial | steel | — | 8538 | пл. 1884 | 0.61 | `#9AACBB` | 2 | 1 |

## Чугуны

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Fe:93.9,C:3.4,Si:2.2,Mn:0.5` | partial | cast_iron | — | 7552 | L 1471 | 0.61 | `#93A6B3` | 3, 2 | 2, 1 |
| `Fe:94.25,C:3.2,Si:2.1,Mn:0.45` | partial | cast_iron | — | 7570 | L 1495 | 0.61 | `#94A6B4` | 3, 2 | 2, 1 |
| `Fe:96,C:3,Si:0.5,Mn:0.5` | partial | cast_iron | — | 7669 | — | 0.62 | `#94A5B4` | 2 | 2, 1, 3 |
| `Fe:95.85,C:2.5,Si:1.3,Mn:0.35` | partial | cast_iron | — | 7654 | — | 0.62 | `#96A7B7` | 2 | 2, 1, 3 |
| `Fe:93.55,C:3.6,Si:2.5,Mn:0.3,Mg:0.05` | partial | cast_iron | — | 7523 | — | 0.61 | `#92A7B2` | 2 | 2, 1, 3 |
| `Fe:93.25,C:3.8,Si:2.6,Mn:0.3,Mg:0.05` | partial | cast_iron | — | 7506 | — | 0.61 | `#92A5B2` | 2 | 2, 1, 3 |
| `Fe:93.88,C:3.6,Si:2.2,Mn:0.3,Mg:0.02` | partial | cast_iron | — | 7541 | — | 0.61 | `#92A7B2` | 2 | 2, 1, 3 |
| `Fe:69.9,C:2.8,Cr:25,Mo:1,Si:0.8,Mn:0.5` | partial | cast_iron | — | 7507 | — | 0.24 | `#9EB3C0` | 2 | 2, 1, 3 |
| `Fe:77.5,C:3,Ni:15,Cr:2,Si:2,Mn:0.5` | partial | cast_iron | — | 7726 | — | 0.59 | `#AAC29E` | 2 | 2, 1, 3 |
| `Fe:93.8,C:3.1,Si:1.8,P:0.8,Mn:0.5` | partial | cast_iron | — | 7543 | — | 0.61 | `#8FAFA7` | 2 | 2, 1, 3 |

## Цветные сплавы

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Al:95,Mg:5` | ok | nonferrous | 25.0 | 2652 | пл. 900 | 0.20 | `#C9EAF4` | 2 | — |
| `Al:94,Cu:4,Mg:1,Mn:1` | ok | nonferrous | 104.8 | 2987 | пл. 926 | 0.20 | `#F4BAB8` | 2 | — |
| `Al:88,Si:12` | ok | nonferrous | 28.6 | 2656 | пл. 917 | 0.20 | `#C8EFF4` | 2 | — |
| `Cu:70,Zn:30` | ok | nonferrous | 130.7 | 8412 | пл. 1227 | 0.17 | `#D5AB37` | 2 | — |
| `Cu:88,Sn:12` | ok | nonferrous | 196.2 | 8759 | пл. 1290 | 0.01 | `#FF7452` | 2 | — |
| `Cu:70,Ni:30` | ok | nonferrous | 181.9 | 8942 | пл. 1420 | 0.00 | `#FA896D` | 2 | — |
| `Ti:90,Al:6,V:4` | ok | nonferrous | 454.3 | 4457 | пл. 1884 | 0.09 | `#A9BFCD` | 2 | — |
| `Ni:61,Cr:22,Mo:9,Nb:3.5,Fe:3.5,Co:1` | ok | nonferrous | 353.4 | 8584 | пл. 1782 | 0.02 | `#D7D2B1` | 2 | — |
| `Sn:60,Pb:40` | ok | nonferrous | 45.5 | 8892 | пл. 461 | 0.18 | `#B9C7E1` | 2 | — |
| `Ag:92.5,Cu:7.5` | ok | nonferrous | 76.5 | 10384 | пл. 1236 | 0.00 | `#F9B0AE` | 2 | — |

## Керамика и композиты

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Al:52.93,O:47.07` | partial | Al2O3 | — | 3970 | пл. 2327 | — | `#C7DEFD` | 4, 5 | 4, 5, 6 |
| `Zr:74.03,O:25.97` | partial | ZrO2 | — | 5680 | — | — | `#C4B59A` | 6 | 4, 7, 5, 6 |
| `Si:60.06,N:39.94` | partial | Si3N4 | — | 3200 | разл./субл. 2187 | — | `#A1E0D7` | 7, 8 | 4, 5, 6 |
| `Al:65.83,N:34.17` | partial | AlN | — | 3260 | разл./субл. 2826 | — | `#CCE0F9` | 7, 9 | 4, 5, 6 |
| `Si:46.74,O:53.26` | partial | SiO2 | — | 2640 | — | — | `#A0DEE6` | 10 | 4, 7, 5, 6 |
| `Mg:17.08,Al:37.93,O:44.99` | partial | MgAl2O4 | — | 3578 | — | — | `#BEE0EC` | 11 | 4, 7, 5, 6 |
| `Mg:8.31,Al:18.45,Si:24.01,O:49.23` | partial | Mg2Al4Si5O18 | — | 2512 | — | — | `#AFE3E7` | 12 | 4, 7, 5, 6 |
| `Ca:29.48,Ti:35.21,O:35.31` | partial | CaTiO3 | — | 4036 | — | — | `#B3A8CB` | 11 | 4, 7, 5, 6 |
| `Al:42.34,Zr:14.81,O:42.85` | partial | alumina-zirconia-80-20? | — | — | — | — | `#C2D3ED` | — | 8, 9 |
| `Zr:68.11,Y:6.3,O:25.59` | partial | zirconia-yttria-92-8? | — | — | — | — | `#C7AC97` | — | 8, 9 |

## Карбиды и твёрдые сплавы

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `Fe:93.31,C:6.69` | partial | Fe3C | — | 7690 | — | — | `#8995A7` | 13 | 4, 7, 5, 6 |
| `W:93.87,C:6.13` | partial | WC | — | 15770 | разл. 3028 | — | `#63707A` | 14, 13 | 4, 5, 6 |
| `Ti:79.94,C:20.06` | partial | TiC | — | 4910 | пл. 3326 | — | `#72808A` | 7, 15 | 4, 5, 6 |
| `Si:70.04,C:29.96` | partial | SiC | — | 3210 | разл./субл. 3281 | — | `#568776` | 7, 16 | 4, 5, 6 |
| `B:78.26,C:21.74` | partial | B4C | — | — | пл. 2779 | — | `#487C82` | 7 | 4, 10, 5, 6 |
| `Cr:86.66,C:13.34` | partial | Cr3C2 | — | 6740 | — | — | `#9FB4C1` | 13 | 4, 7, 5, 6 |
| `Mo:94.11,C:5.89` | partial | Mo2C | — | 9180 | — | — | `#63707A` | 13 | 4, 7, 5, 6 |
| `Ta:93.78,C:6.22` | partial | TaC | — | 14400 | пл. 3964–4118 | — | `#63707A` | 17, 13 | 4, 5, 6 |
| `Nb:88.55,C:11.45` | partial | NbC | — | 7820 | пл. 3773 | — | `#606A74` | 18, 13 | 4, 5, 6 |
| `W:84.48,C:5.52,Co:10` | partial | cermet | — | 14520 | — | 0.52 | `#6D7A86` | 19, 2 | 11, 1, 3 |

## Абсурдные и пограничные

| Состав | Статус | Фаза/режим | HV | кг/м³ | Нагрев, K | Склонность к коррозии | Цвет | Ист. | Диаг. |
|---|---|---|---:|---:|---|---:|---|---|---|
| `C:99.9,Fe:0.1` | unsupported | mixture | — | — | — | — | `#31363B` | — | 12 |
| `Fe:50,He:50` | unsupported | mixture | — | — | — | — | `#AFC1DA` | — | 13 |
| `Fe:40,Ne:30,Ar:30` | unsupported | mixture | — | — | — | — | `#B1C3DE` | — | 13 |
| `Au:50,Xe:25,Kr:25` | unsupported | mixture | — | — | — | — | `#FAD139` | — | 13 |
| `Hg:50,Na:50` | ok | nonferrous | 49.3 | 7252 | пл. 197 | 0.43 | `#BFB592` | 2 | 14 |
| `U:30,Th:30,He:40` | unsupported | mixture | — | — | — | — | `#97CEB5` | — | 13 |
| `Ce:25,Nd:25,La:25,Ar:25` | unsupported | mixture | — | — | — | — | `#CC9BA6` | — | 13 |
| `O:70,Fe:30` | partial | compound_or_mixture | — | — | — | — | `#AFCAEE` | — | 8, 9 |
| `Fe:50,Cl:50` | unsupported | mixture | — | — | — | — | `#BDD793` | — | 13 |
| `Pu:20,C:40,Rn:40` | unsupported | mixture | — | — | — | — | `#616785` | — | 13 |
| `C:0.9,Fe:0.1` | unsupported | mixture | — | — | — | — | `#3A4246` | — | 12 |
| `Fe:0.5,He:0.5` | unsupported | mixture | — | — | — | — | `#AFC1DA` | — | 13 |
| `U:0.001,Th:0.999` | ok | nonferrous | 26.4 | 11707 | пл. 2023 | 0.66 | `#8ABD59` | 2 | — |
| `La:0.333,Ce:0.333,Nd:0.334` | ok | nonferrous | 78.4 | 6644 | пл. 1202 | 0.17 | `#CA888A` | 2 | — |
| `Fe:0.999999,C:0.000001` | ok | steel | 98.3 | 7870 | S 1811, L 1811 | 0.63 | `#A5B3C8` | 1, 2 | — |

## Источники оценок

1. [phase_diagram_interpolation](https://www.gotrawama.eu/Siderurgia/The%20C-Fe%20%28Carbon-Iron%29%20System.pdf)
2. empirical · material-calc empirical gameplay model
3. [reference_correlation](https://doi.org/10.2320/matertrans.F-M2019829)
4. [reference](https://srd.nist.gov/JPCRD/jpcrd120.pdf)
5. [reference](https://pdg.lbl.gov/AtomicNuclearProperties/HTML/aluminum_oxide_sapphire.html)
6. [reference](https://nanomaterials.iolitec.de/sites/nanomaterials.iolitec.de/files/2025-12/TDS%20NO-0013-UP%20ZrO2%2020-30%20nm.pdf)
7. [reference](https://srdata.nist.gov/CeramicDataPortal/Scd/Z00181)
8. [reference](https://srdata.nist.gov/CeramicDataPortal/Scd/Z00431)
9. [reference](https://srdata.nist.gov/CeramicDataPortal/Scd/Z00220)
10. [reference](https://srdata.nist.gov/CeramicDataPortal/Scd/Z00788)
11. [reference](https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nbsmonograph25-9.pdf)
12. [reference](https://www.govinfo.gov/content/pkg/GOVPUB-C13-85c072925c6df005be340a7fc4f4c98e/pdf/GOVPUB-C13-85c072925c6df005be340a7fc4f4c98e.pdf)
13. [reference](https://ntrs.nasa.gov/api/citations/19960020445/downloads/19960020445.pdf)
14. [reference](https://doi.org/10.1111/j.1151-2916.1965.tb14731.x)
15. [reference](https://www.govinfo.gov/content/pkg/GOVPUB-C13-b1067c399c32a6af99ac554f24c243b6/pdf/GOVPUB-C13-b1067c399c32a6af99ac554f24c243b6.pdf)
16. [reference](https://www.sicrystal.de/index.php/en/properties-en)
17. [reference](https://doi.org/10.1080/17436753.2018.1510819)
18. [reference](https://www.osti.gov/servlets/purl/967387)
19. empirical_phase_mixture · material-calc empirical gameplay model

## Диагностика

1. `hardness_requires_microstructure` · Hardness for this material needs a microstructure or a calibrated processing profile.
2. `cast_iron_microstructure_unresolved` · Cast-iron subtype requires graphite morphology, processing or measured phase data.
3. `thermal_model_unavailable` · No applicable thermal transition model is available for this composition.
4. `phase_assumed` · Фаза предположена по стехиометрии.
5. `hardness_requires_microstructure` · Hardness needs phase-specific data for the material's microstructure and processing.
6. `other_properties_unavailable` · No applicable elastic, neutron or corrosion model is configured for this phase.
7. `thermal_data_unavailable` · No applicable phase transition data is available.
8. `phase_assembly_required` · The elemental composition may describe a compound or a phase mixture; select a matching profile or specify the phases.
9. `properties_unavailable` · Thermal, density, hardness and corrosion estimates need the material's phases.
10. `density_unavailable` · No applicable phase density is available.
11. `cermet_phases_assumed` · Carbide and binder fractions are estimated from the composition.
12. `nonmetallic_material_unresolved` · No reference phase or applicable metallic model for this composition.
13. `unresolved_gases_or_halogens` · At least 2 wt% is noble gas or halogen without an identified bound phase; outside the alloy model domain.
14. `volatile_components` · Есть летучие компоненты при заданной температуре.
