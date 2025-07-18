# pipe_data.py

# Pipe roughness coefficients from standard references
roughness = {
    'Seamless Steel': 0.061,
    'Stainless Steel': 0.006,
    'Carbon Steel': 0.05,
    'Tubing': 0.002,
    'HDPE': 0.015
}

# Pipe Young's Modulus (E) values in MPa (10^6 N/m2)
modulus = {
    'ABS Plastics': None,
    'Acrylic': None,
    'Aluminium': 6.90e4,
    'Aluminium Bronze': 1.20e3,
    'Carbon Fiber Reinforced Plastic': 1.50e3,
    'Hastelloy C': 2.00e3,
    'Inconel': 2.00e3,
    'Polyethylene, HDPE-PE80': 1050,
    'Polyethylene, HDPE-PE100': 1380,
    'Polyethylene, LDPE': 520,
    'PVC': 4.83e3,
    'Stainless Steel, AISI 302': 1.80e3,
    'Stainless Steel, AISI 304': 1.95e3,
    'Stainless Steel, AISI 316': 1.93e3,
    'Steel Carbon, Mild (to ASME B36.10)': 2.0e3
}

# Alias (mapping) from common names to reference keys
material_aliases = {
    'hdpe': 'Polyethylene, HDPE-PE100',
    'carbon steel': 'Steel Carbon, Mild (to ASME B36.10)',
    'stainless steel': 'Stainless Steel, AISI 304'   # Stainless Steel 304 is more common than 316 globally

}
