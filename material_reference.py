"""Local reference phases and nominal material profiles."""

from dataclasses import dataclass

from alloy_models import ElementData

MATCH_TOLERANCE = 0.0025
NIST_CERAMICS = "https://srdata.nist.gov/CeramicDataPortal/Scd/Z00181"
NIST_ALUMINA = "https://srd.nist.gov/JPCRD/jpcrd120.pdf"
NIST_DIFFRACTION = "https://www.govinfo.gov/content/pkg/GOVPUB-C13-b1067c399c32a6af99ac554f24c243b6/pdf/GOVPUB-C13-b1067c399c32a6af99ac554f24c243b6.pdf"
NIST_DIFFRACTION_9 = "https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nbsmonograph25-9.pdf"
NASA_CARBIDES = "https://ntrs.nasa.gov/api/citations/19960020445/downloads/19960020445.pdf"
PDG_ALUMINA = "https://pdg.lbl.gov/AtomicNuclearProperties/HTML/aluminum_oxide_sapphire.html"


@dataclass(frozen=True)
class ReferencePhase:
    atoms: dict[str, int]
    family: str
    density: tuple[float, str, str] | None = None
    transition: tuple[str, float, str, str] | None = None
    transition_range_k: tuple[float, float] | None = None


PHASES = {
    "Al2O3": ReferencePhase(
        {"Al": 2, "O": 3}, "oxide", (3970, PDG_ALUMINA, "Dense alpha alumina (sapphire)"),
        ("melting_point_k", 2327, NIST_ALUMINA, "Alpha alumina"),
    ),
    "ZrO2": ReferencePhase(
        {"Zr": 1, "O": 2}, "oxide", (5680, "https://nanomaterials.iolitec.de/sites/nanomaterials.iolitec.de/files/2025-12/TDS%20NO-0013-UP%20ZrO2%2020-30%20nm.pdf", "Reference density of 20–30 nm zirconium oxide feedstock"),
    ),
    "Si3N4": ReferencePhase(
        {"Si": 3, "N": 4}, "nitride",
        (3200, "https://srdata.nist.gov/CeramicDataPortal/Scd/Z00431", "Representative sintered polycrystalline sample"),
        transition=("decomposition_or_sublimation_k", 2187, NIST_CERAMICS, "Typical decomposition or sublimation"),
    ),
    "AlN": ReferencePhase(
        {"Al": 1, "N": 1}, "nitride",
        (3260, "https://srdata.nist.gov/CeramicDataPortal/Scd/Z00220", "Typical aluminium nitride"),
        transition=("decomposition_or_sublimation_k", 2826, NIST_CERAMICS, "Typical decomposition or sublimation"),
    ),
    "SiO2": ReferencePhase(
        {"Si": 1, "O": 2}, "oxide",
        (2640, "https://srdata.nist.gov/CeramicDataPortal/Scd/Z00788", "Quartz at about 295 K; glass and other polymorphs differ"),
    ),
    "MgAl2O4": ReferencePhase(
        {"Mg": 1, "Al": 2, "O": 4}, "oxide",
        (3578, NIST_DIFFRACTION_9, "Theoretical cubic spinel density at 298 K"),
    ),
    "Mg2Al4Si5O18": ReferencePhase(
        {"Mg": 2, "Al": 4, "Si": 5, "O": 18}, "oxide",
        (2512, "https://www.govinfo.gov/content/pkg/GOVPUB-C13-85c072925c6df005be340a7fc4f4c98e/pdf/GOVPUB-C13-85c072925c6df005be340a7fc4f4c98e.pdf", "Calculated density for hexagonal cordierite at 298 K"),
    ),
    "CaTiO3": ReferencePhase(
        {"Ca": 1, "Ti": 1, "O": 3}, "oxide",
        (4036, NIST_DIFFRACTION_9, "Theoretical density of calcium titanate perovskite at 298 K"),
    ),
    "Y2O3": ReferencePhase(
        {"Y": 2, "O": 3}, "oxide",
        (5030, "https://srdata.nist.gov/CeramicDataPortal/Scd/Z00640", "Theoretical density from lattice parameters"),
    ),
    "Fe3C": ReferencePhase(
        {"Fe": 3, "C": 1}, "carbide", (7690, NASA_CARBIDES, "Cementite; metastable end member"),
    ),
    "WC": ReferencePhase(
        {"W": 1, "C": 1}, "carbide",
        (15770, NASA_CARBIDES, "Dense hexagonal tungsten carbide"),
        transition=("decomposition_k", 3028, "https://doi.org/10.1111/j.1151-2916.1965.tb14731.x", "Alpha WC decomposes to beta WC and carbon"),
    ),
    "TiC": ReferencePhase(
        {"Ti": 1, "C": 1}, "carbide",
        (4910, NIST_DIFFRACTION, "Stoichiometric cubic TiC, ideal density from 4.3274 Å unit cell"),
        ("melting_point_k", 3326, NIST_CERAMICS, "Typical TiC melting point"),
    ),
    "SiC": ReferencePhase(
        {"Si": 1, "C": 1}, "carbide",
        (3210, "https://www.sicrystal.de/index.php/en/properties-en", "Dense 4H/6H silicon carbide"),
        ("decomposition_or_sublimation_k", 3281, NIST_CERAMICS, "Typical decomposition or sublimation"),
    ),
    "B4C": ReferencePhase(
        {"B": 4, "C": 1}, "carbide",
        transition=("melting_point_k", 2779, NIST_CERAMICS, "Typical boron carbide"),
    ),
    "Cr3C2": ReferencePhase(
        {"Cr": 3, "C": 2}, "carbide", (6740, NASA_CARBIDES, "Orthorhombic chromium carbide"),
    ),
    "Mo2C": ReferencePhase(
        {"Mo": 2, "C": 1}, "carbide", (9180, NASA_CARBIDES, "Hexagonal molybdenum carbide"),
    ),
    "TaC": ReferencePhase(
        {"Ta": 1, "C": 1}, "carbide",
        (14400, NASA_CARBIDES, "Dense cubic tantalum carbide"),
        transition=("melting_point_k", 4041, "https://doi.org/10.1080/17436753.2018.1510819", "Stoichiometric laser-melting estimate, reported uncertainty ±77 K"),
        transition_range_k=(3964, 4118),
    ),
    "NbC": ReferencePhase(
        {"Nb": 1, "C": 1}, "carbide",
        (7820, NASA_CARBIDES, "Dense cubic niobium carbide"),
        transition=("melting_point_k", 3773, "https://www.osti.gov/servlets/purl/967387", "Typical NbC melting point"),
    ),
}

# These are nominal oxide blends. Phase reactions during processing are unresolved.
MATERIAL_PROFILES = {
    "alumina-zirconia-80-20": {"Al2O3": 0.80, "ZrO2": 0.20},
    "zirconia-yttria-92-8": {"ZrO2": 0.92, "Y2O3": 0.08},
}


def phase_composition(phase: ReferencePhase, db: dict[str, ElementData]) -> dict[str, float]:
    if any(symbol not in db or db[symbol].atomic_mass <= 0 for symbol in phase.atoms):
        return {}
    masses = {symbol: count * db[symbol].atomic_mass for symbol, count in phase.atoms.items()}
    total = sum(masses.values())
    return {symbol: mass / total for symbol, mass in masses.items()}


def profile_composition(profile_id: str, db: dict[str, ElementData]) -> dict[str, float]:
    if profile_id not in MATERIAL_PROFILES:
        raise ValueError(f"Unknown material profile '{profile_id}'. Choose from: {', '.join(MATERIAL_PROFILES)}")
    composition: dict[str, float] = {}
    for formula, fraction in MATERIAL_PROFILES[profile_id].items():
        phase = phase_composition(PHASES[formula], db)
        if not phase:
            raise ValueError(f"Element data is incomplete for {formula} in profile '{profile_id}'")
        for symbol, mass in phase.items():
            composition[symbol] = composition.get(symbol, 0.0) + fraction * mass
    return composition


def composition_matches(composition: dict[str, float], reference: dict[str, float]) -> bool:
    return composition.keys() == reference.keys() and all(
        abs(mass - reference[symbol]) <= MATCH_TOLERANCE for symbol, mass in composition.items()
    )


def reference_candidates(composition: dict[str, float], db: dict[str, ElementData]) -> tuple[list[str], list[str]]:
    phases = [
        formula for formula, phase in PHASES.items()
        if composition.keys() == phase.atoms.keys() and composition_matches(composition, phase_composition(phase, db))
    ]
    profiles = []
    for profile_id, phases_by_mass in MATERIAL_PROFILES.items():
        symbols = set().union(*(PHASES[formula].atoms for formula in phases_by_mass))
        if symbols == composition.keys() and all(symbol in db and db[symbol].atomic_mass > 0 for symbol in symbols):
            if composition_matches(composition, profile_composition(profile_id, db)):
                profiles.append(profile_id)
    return phases, profiles
