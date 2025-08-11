# Advanced Centrifugal Pump Sizing Calculation
# Built by Louis Walker, Process Engineer, 2025

# Import Key Modules and Programs Here
import tkinter as tk
from tkinter import messagebox
from Hydraulics_Script_Advanced_Core_Working import calculate_pressure_drop
from thermo.chemical import Chemical
from thermo.vapor_pressure import VaporPressure

#--------Define Atmospheric Pressure at Altitude Given by User----------
#---------Generally this is irrelevant, it has been built in for completeness only---------------
def atmospheric_pressure(altitude_m):
    """
    Calculates atmospheric pressure in Pascals at a given altitude in meters,
    using the barometric formula (valid up to ~11,000 m).
    """
    P0 = 101325      # sea level standard atmospheric pressure, Pa
    T0 = 288.15      # sea level standard temperature, K
    L = 0.0065       # temperature lapse rate, K/m
    R = 8.314462618     # universal gas constant, J/(mol·K)
    M = 0.02896968  # molar mass of Earth's air, kg/mol
    g = 9.80665      # gravity, m/s^2

    if altitude_m < 0:
        altitude_m = 0  # Clamp negative altitudes to sea level

    T = T0 - L * altitude_m
    if T <= 0:
        raise ValueError("Altitude too high causing non-physical temperature")

    # barometric formula
    P = P0 * (T / T0) ** (g * M / (R * L))
    return P  # Pa


class FluidInputDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Fluid and Temperature Input")
        self.grab_set()  # Make this window modal

        tk.Label(self, text="Fluid Name (e.g. Water):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Label(self, text="Min Pumping Temperature (°C):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Label(self, text="Max Pumping Temperature (°C):").grid(row=2, column=0, sticky="e", padx=5, pady=5)

        self.fluid_name_var = tk.StringVar()
        self.min_temp_var = tk.StringVar()
        self.max_temp_var = tk.StringVar()

        self.entry_fluid = tk.Entry(self, textvariable=self.fluid_name_var)
        self.entry_min_temp = tk.Entry(self, textvariable=self.min_temp_var)
        self.entry_max_temp = tk.Entry(self, textvariable=self.max_temp_var)

        self.entry_fluid.grid(row=0, column=1, padx=5, pady=5)
        self.entry_min_temp.grid(row=1, column=1, padx=5, pady=5)
        self.entry_max_temp.grid(row=2, column=1, padx=5, pady=5)

        self.btn_ok = tk.Button(self, text="OK", command=self.on_ok)
        self.btn_cancel = tk.Button(self, text="Cancel", command=self.destroy)

        self.btn_ok.grid(row=3, column=0, pady=10)
        self.btn_cancel.grid(row=3, column=1, pady=10)

        self.result = None

    def on_ok(self):
        fluid = self.fluid_name_var.get().strip()
        min_temp_str = self.min_temp_var.get().strip()
        max_temp_str = self.max_temp_var.get().strip()

        if not fluid:
            messagebox.showerror("Input Error", "Please enter a fluid name.")
            return

        try:
            min_temp = float(min_temp_str)
            max_temp = float(max_temp_str)
        except ValueError:
            messagebox.showerror("Input Error", "Enter valid numeric values for temperatures.")
            return

        if max_temp < min_temp:
            messagebox.showerror("Input Error", "Max temperature must be greater than or equal to Min temperature.")
            return

        self.result = (fluid, min_temp, max_temp)
        self.destroy()


def get_fluid_info(root):
    dialog = FluidInputDialog(root)
    root.wait_window(dialog)

    if dialog.result:
        fluid_name, min_temp, max_temp = dialog.result

        try:
            fluid_min = Chemical(fluid_name, T=min_temp + 273.15)
            density_min = fluid_min.rho
            viscosity_min = fluid_min.mu * 1000  # Pa.s to cP
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Failed to calculate fluid properties at min temperature: {e}")
            root.destroy()
            exit()



        return {
            "fluid_name": fluid_name,
            "min_temp_C": min_temp,
            "max_temp_C": max_temp,
            "density": density_min,
            "viscosity_cP": viscosity_min,
        }
        
    else:
        root.destroy()
        exit()
    

def pump_sizing(suction_pressure_drop_kPa, discharge_pressure_drop_kPa, flow_rate_m3hr, suction_elev_diff,total_elevation_diff, max_dest_pressure,density= 1000, efficiency=0.75, vapor_pressure_kPa= 6, altitude_m =400):
    g = 9.81
    margin = 1 # Define NPSH_a margin, usually 0.8-1m
    Q_m3s = flow_rate_m3hr / 3600
    atmospheric_Pa = atmospheric_pressure(altitude_m ) # Determines the atmospheric pressure
    atmospheric_head = atmospheric_Pa/(density*g) # Converts atmospheric pressure (Pa) to head (m) using fluid density and grav. constant
    vapor_pressure_head = (vapor_pressure_kPa*1000)/(density*g) # Converts vapor pressure (kPa) to (m) using fluid density and grav. constant
    suction_loss_head = suction_pressure_drop_kPa*1000/(density*g) # Converts suction pressure drop (kPa) to (m) using fluid density and grav. constant
    discharge_loss_head = discharge_pressure_drop_kPa*1000/(density*g) # Converts suction pressure drop (kPa) to (m) using fluid density and grav. constant 
    max_req_dist_head= max_dest_pressure*1000/(density * g ) # Maximum head to be overcome (m) due to final destination pressure
    #---------------------------------Calculate the NPSH_a including a 1 m margin------------- 
    NPSH_a = atmospheric_head + suction_elev_diff - suction_loss_head -vapor_pressure_head # NPSH_a in m

    #---------------Calculate dynamic head from pressure drop H = ΔP / (ρ g) and static elevation diff.------------
    
    total_dynamic_head_req = suction_loss_head + discharge_loss_head + total_elevation_diff + max_req_dist_head # Total dynamic head required in (m)
    
    #-------------------------------Calculate Requited Power------------------------------
    
    # Hydraulic power in Watts
    power_hydraulic_W = density * g * Q_m3s * total_dynamic_head_req

    if efficiency <= 0 or efficiency > 1:
        raise ValueError("Pump efficiency should be between 0 and 1")

    power_brake_W = power_hydraulic_W / efficiency

    return {
        "pump_head_m": total_dynamic_head_req,
        "hydraulic_power_kW": power_hydraulic_W / 1000,
        "brake_power_kW": power_brake_W / 1000,
        "NPSHA": NPSH_a,
        "NPSHA_margin_included": NPSH_a - margin
    }


def on_calculate(fluid_props):
    try:
        flow_rate = float(flow_rate_entry.get())
        if flow_rate <= 0:
            raise ValueError("Flowrate must be positive")
        
        pump_centreline = float(pump_centreline_entry.get())
        suction_source = float(suction_source_entry.get())
        discharge_height = float(discharge_height_entry.get())
        max_dest_pressure = float(max_dest_pressure_entry.get())
    except ValueError as e:
        messagebox.showerror("Input Error", f"Invalid input: {e}")
        return
    
    total_elevation_diff = discharge_height - suction_source  # Net elevation difference pump must overcome
    suction_elev_diff = suction_source - pump_centreline # Elevation difference in suction line (i.e. required static suction lift) in (m)
    max_dest_pressure = max_dest_pressure  # Maximum pressure at destination in kPa
    # Example segment data for suction line (customize as needed)
    segments_suction = [{
        "length": 50,  # meters
        "material": "Carbon Steel",
        "Nom_D": 3,  # inches
        "schedule": "40",
        # Add fittings and valves as needed...
    }]
    segments_discharge = [{
        "length": 150,  # meters
        "material": "Carbon Steel",
        "Nom_D": 3,  # inches
        "schedule": "40",
        # Add fittings and valves as needed...
    }]
    
    density = fluid_props["density"]
    viscosity = fluid_props["viscosity_cP"]
        # Calculate vapor pressure at max temp and altitude = pump centreline elevation
    try:
        fluid_at_max = Chemical(fluid_props["fluid_name"], T=fluid_props["max_temp_C"] + 273.15)
        # VaporPressure expects temperature in K and pressure returned in Pa
        # Adjust vapor pressure for atmospheric pressure at pump elevation:
        vapor_pressure_Pa = fluid_at_max.VaporPressure(fluid_props["max_temp_C"] + 273.15)
        
        # Atmospheric pressure at pump centreline elevation:
        atm_pressure_Pa = atmospheric_pressure(pump_centreline)

        # Vapor pressure can be adjusted by the ratio of local atm pressure to sea level, 
        # but often VaporPressure already accounts for temperature only.
        # For safety, use vapor pressure as-is (Pa), convert to kPa:
        vapor_pressure_kPa = vapor_pressure_Pa / 1000
    except Exception:
        vapor_pressure_kPa = 0  # Or fallback to some safe default if needed
    vapor_pressure = vapor_pressure_kPa
    # Calculate pressure drop using your hydraulics core
    results_suction = calculate_pressure_drop(segments_suction, density, viscosity, flow_rate)
    suction_pressure_drop_kPa = results_suction["total_pressure_drop_kPa"]
    results_discharge = calculate_pressure_drop(segments_discharge, density, viscosity, flow_rate)
    discharge_pressure_drop_kPa = results_discharge["total_pressure_drop_kPa"]

    # Pump sizing, assume 0 elevation head and 75% efficiency
    sizing_results = pump_sizing(suction_pressure_drop_kPa, discharge_pressure_drop_kPa, flow_rate, suction_elev_diff, total_elevation_diff,
                                density=density, efficiency=0.75,vapor_pressure_kPa = vapor_pressure,altitude_m=pump_centreline, max_dest_pressure=max_dest_pressure)


    # After calculating NPSHA and NPSHA_margin_included inside your pump sizing logic:
    warnings = []

    # Simple NPSH_A warning handling
    if sizing_results["NPSHA"] < 0:
        warnings.append("NPSH_A is negative — cavitation certain. Consider increasing suction size, lowering pump, or reducing temperature.")
    elif sizing_results["NPSHA"] < 1.0:
        warnings.append("NPSH_A is very low — risk of cavitation. Consider increasing suction size, lowering pump, or reducing temperature.")

    # Attach warnings to results so GUI can display
    sizing_results["warnings"] = warnings
    
    msg = (
        f"Fluid: {fluid_props['fluid_name']}\n"
        f"Min Temp: {fluid_props['min_temp_C']} °C, Max Temp: {fluid_props['max_temp_C']} °C\n"
        f"Density @ Min Temp: {density:.2f} kg/m³\n"
        f"Viscosity @ Min Temp: {viscosity:.3f} cP\n"
        f"Vapor Pressure @ Max Temp: {vapor_pressure_kPa:.3f} kPa\n\n"
        f"Total Pressure Drop in Suction Line: {suction_pressure_drop_kPa:.3f} kPa\n"
        f"Pump Head Required: {sizing_results['pump_head_m']:.3f} m\n"
        f"Hydraulic Power: {sizing_results['hydraulic_power_kW']:.3f} kW\n"
        f"Brake Power (75% efficiency): {sizing_results['brake_power_kW']:.3f} kW\n"
        f"NPSH_A (75% efficiency): {sizing_results['NPSHA']:.3f} m\n"
        f"NPSH_A (Including margin): {sizing_results['NPSHA_margin_included']:.3f} m"
    )

    messagebox.showinfo("Pump Sizing Results", msg)

    # After showing normal results
    if sizing_results.get("warnings"):
        warning_msg = "\nWarnings:\n"
        for w in sizing_results["warnings"]:
            warning_msg += f" - {w}\n"
        messagebox.showwarning("Pump Sizing Warnings", warning_msg)
#-------------------------------------------------Main Running Script Section------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window initially

    fluid_properties = get_fluid_info(root)

    root.deiconify()
    root.title("Pump Sizing Calculator")

    #--------------------Create a dialog box to ask user for flowrate, and relevant elevations

    tk.Label(root, text="Enter flow rate (m3/h):").grid(row=0, column=0, padx=10, pady=10)
    flow_rate_entry = tk.Entry(root)
    flow_rate_entry.grid(row=0, column=1, padx=10, pady=10)
    # Pump heights inputs
    tk.Label(root, text="Pump Centreline Height (m):").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    pump_centreline_entry = tk.Entry(root)
    pump_centreline_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(root, text="Suction Source Height (m):").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    suction_source_entry = tk.Entry(root)
    suction_source_entry.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(root, text="Discharge Height (m):").grid(row=3, column=0, padx=10, pady=5, sticky='e')
    discharge_height_entry = tk.Entry(root)
    discharge_height_entry.grid(row=3, column=1, padx=10, pady=5)
    
    tk.Label(root, text="Maximum Required Destination Pressure (kPa):").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    max_dest_pressure_entry = tk.Entry(root)
    max_dest_pressure_entry.grid(row=4, column=1, padx=10, pady=5)


    calc_button = tk.Button(root, text="Calculate Pump Size",
                            command=lambda: on_calculate(fluid_properties))
    calc_button.grid(row=5, column=0, columnspan=2, pady=10)

    root.mainloop()