# Advanced Centrifugal Pump Sizing Calculation
# Built by Louis Walker, Process Engineer, 2025

# Import Key Modules and Programs Here
import tkinter as tk
from tkinter import messagebox
from Hydraulics_Script_Advanced_Core_Working import calculate_pressure_drop
from thermo.chemical import Chemical
from thermo.vapor_pressure import VaporPressure
import numpy as np
import matplotlib.pyplot as plt

#--------Define Atmospheric Pressure at Altitude Given by User----------
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


class FlowRangeDialog(tk.Toplevel):
    """Dialog to get flow range parameters for curve plotting"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Flow Range for Curve Generation")
        self.grab_set()
        
        tk.Label(self, text="Minimum Flow Rate (m³/h):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        tk.Label(self, text="Maximum Flow Rate (m³/h):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        tk.Label(self, text="Number of Points:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        
        self.flow_min_var = tk.StringVar(value="10")
        self.flow_max_var = tk.StringVar(value="100")
        self.num_points_var = tk.StringVar(value="20")
        
        self.entry_flow_min = tk.Entry(self, textvariable=self.flow_min_var)
        self.entry_flow_max = tk.Entry(self, textvariable=self.flow_max_var)
        self.entry_num_points = tk.Entry(self, textvariable=self.num_points_var)
        
        self.entry_flow_min.grid(row=0, column=1, padx=5, pady=5)
        self.entry_flow_max.grid(row=1, column=1, padx=5, pady=5)
        self.entry_num_points.grid(row=2, column=1, padx=5, pady=5)
        
        self.btn_ok = tk.Button(self, text="Generate Curves", command=self.on_ok)
        self.btn_cancel = tk.Button(self, text="Cancel", command=self.destroy)
        
        self.btn_ok.grid(row=3, column=0, pady=10)
        self.btn_cancel.grid(row=3, column=1, pady=10)
        
        self.result = None
    
    def on_ok(self):
        try:
            flow_min = float(self.flow_min_var.get())
            flow_max = float(self.flow_max_var.get())
            num_points = int(self.num_points_var.get())
            
            if flow_min <= 0 or flow_max <= 0:
                raise ValueError("Flow rates must be positive")
            if flow_max <= flow_min:
                raise ValueError("Max flow must be greater than min flow")
            if num_points < 2:
                raise ValueError("Need at least 2 points")
                
            self.result = (flow_min, flow_max, num_points)
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))


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
    

def pump_sizing(suction_pressure_drop_kPa, discharge_pressure_drop_kPa, flow_rate_m3hr, suction_elev_diff,
                total_elevation_diff, max_dest_pressure, density=1000, efficiency=0.75, 
                vapor_pressure_kPa=6, altitude_m=400):
    g = 9.81
    margin = 1 # Define NPSH_a margin, usually 0.8-1m
    Q_m3s = flow_rate_m3hr / 3600
    atmospheric_Pa = atmospheric_pressure(altitude_m) # Determines the atmospheric pressure
    atmospheric_head = atmospheric_Pa/(density*g) # Converts atmospheric pressure (Pa) to head (m)
    vapor_pressure_head = (vapor_pressure_kPa*1000)/(density*g) # Converts vapor pressure (kPa) to (m)
    suction_loss_head = suction_pressure_drop_kPa*1000/(density*g) # Converts suction pressure drop (kPa) to (m)
    discharge_loss_head = discharge_pressure_drop_kPa*1000/(density*g) # Converts discharge pressure drop (kPa) to (m)
    max_req_dist_head = max_dest_pressure*1000/(density * g) # Maximum head to be overcome (m)
    
    # Calculate the NPSH_a
    NPSH_a = atmospheric_head + suction_elev_diff - suction_loss_head - vapor_pressure_head # NPSH_a in m

    # Calculate dynamic head
    total_dynamic_head_req = suction_loss_head + discharge_loss_head + total_elevation_diff + max_req_dist_head
    
    # Calculate Required Power
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


def run_flow_curve(fluid_props, flow_min, flow_max, num_points, other_inputs):
    """
    Runs pump sizing over a range of flow rates and returns results for plotting/comparison.
    """
    flow_rates = np.linspace(flow_min, flow_max, num_points)
    npsha_list = []
    pump_head_list = []
    brake_power_list = []

    for Q in flow_rates:
        # Calculate pressure drops for suction and discharge
        results_suction = calculate_pressure_drop(
            other_inputs["segments_suction"], 
            fluid_props["density"], 
            fluid_props["viscosity_cP"], 
            Q
        )
        suction_pressure_drop_kPa = results_suction["total_pressure_drop_kPa"]
        
        results_discharge = calculate_pressure_drop(
            other_inputs["segments_discharge"],
            fluid_props["density"],
            fluid_props["viscosity_cP"],
            Q
        )
        discharge_pressure_drop_kPa = results_discharge["total_pressure_drop_kPa"]
        
        sizing_results = pump_sizing(
            suction_pressure_drop_kPa,
            discharge_pressure_drop_kPa,
            Q,
            other_inputs["suction_elev_diff"],
            other_inputs["total_elevation_diff"],
            max_dest_pressure=other_inputs["max_dest_pressure"],
            density=fluid_props["density"],
            efficiency=other_inputs.get("efficiency", 0.75),
            vapor_pressure_kPa=other_inputs.get("vapor_pressure_kPa", 0),
            altitude_m=other_inputs.get("altitude_m", 0)
        )
        
        npsha_list.append(sizing_results["NPSHA"])
        pump_head_list.append(sizing_results["pump_head_m"])
        brake_power_list.append(sizing_results["brake_power_kW"])
    
    return {
        "flow_rates": flow_rates,
        "NPSHA": npsha_list,
        "pump_head": pump_head_list,
        "brake_power": brake_power_list
    }


def plot_curve(results, fluid_name):
    """Enhanced plotting function with both NPSH_A and Head on same plot"""
    flow = results["flow_rates"]
    npsha = results["NPSHA"]
    head = results["pump_head"]
    
    # Create figure with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Plot pump head on primary y-axis
    color = 'tab:blue'
    ax1.set_xlabel('Flow Rate (m³/h)', fontsize=12)
    ax1.set_ylabel('Pump Head (m)', color=color, fontsize=12)
    line1 = ax1.plot(flow, head, color=color, linewidth=2, marker='o', 
                     markersize=5, label='Pump Head')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3)
    
    # Create secondary y-axis for NPSH_A
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('NPSH_A (m)', color=color, fontsize=12)
    line2 = ax2.plot(flow, npsha, color=color, linewidth=2, marker='s', 
                     markersize=5, label='NPSH_A', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Add horizontal line at NPSH_A = 0 for reference
    ax2.axhline(y=0, color='red', linestyle=':', alpha=0.5, label='NPSH_A = 0 (Cavitation)')
    
    # Title and legend
    ax1.set_title(f'Pump Performance Curves - {fluid_name}', fontsize=14, fontweight='bold')
    
    # Combine legends from both axes
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right')
    
    plt.tight_layout()
    plt.show()


def on_calculate(fluid_props, entries):
    """Modified to accept entries dict"""
    try:
        flow_rate = float(entries['flow_rate'].get())
        if flow_rate <= 0:
            raise ValueError("Flowrate must be positive")
        
        pump_centreline = float(entries['pump_centreline'].get())
        suction_source = float(entries['suction_source'].get())
        discharge_height = float(entries['discharge_height'].get())
        max_dest_pressure = float(entries['max_dest_pressure'].get())
    except ValueError as e:
        messagebox.showerror("Input Error", f"Invalid input: {e}")
        return
    
    total_elevation_diff = discharge_height - suction_source
    suction_elev_diff = suction_source - pump_centreline
    
    # Example segment data (customize as needed)
    segments_suction = [{
        "length": 50,
        "material": "Carbon Steel",
        "Nom_D": 3,
        "schedule": "40",
    }]
    segments_discharge = [{
        "length": 150,
        "material": "Carbon Steel",
        "Nom_D": 3,
        "schedule": "40",
    }]
    
    density = fluid_props["density"]
    viscosity = fluid_props["viscosity_cP"]
    
    # Calculate vapor pressure at max temp
    try:
        fluid_at_max = Chemical(fluid_props["fluid_name"], T=fluid_props["max_temp_C"] + 273.15)
        vapor_pressure_Pa = fluid_at_max.VaporPressure(fluid_props["max_temp_C"] + 273.15)
        vapor_pressure_kPa = vapor_pressure_Pa / 1000
    except Exception:
        vapor_pressure_kPa = 0
    
    # Calculate pressure drops
    results_suction = calculate_pressure_drop(segments_suction, density, viscosity, flow_rate)
    suction_pressure_drop_kPa = results_suction["total_pressure_drop_kPa"]
    results_discharge = calculate_pressure_drop(segments_discharge, density, viscosity, flow_rate)
    discharge_pressure_drop_kPa = results_discharge["total_pressure_drop_kPa"]

    # Pump sizing
    sizing_results = pump_sizing(
        suction_pressure_drop_kPa, discharge_pressure_drop_kPa, flow_rate, 
        suction_elev_diff, total_elevation_diff,
        density=density, efficiency=0.75, vapor_pressure_kPa=vapor_pressure_kPa,
        altitude_m=pump_centreline, max_dest_pressure=max_dest_pressure
    )

    # Warning handling
    warnings = []
    if sizing_results["NPSHA"] < 0:
        warnings.append("NPSH_A is negative — cavitation certain. Consider increasing suction size, lowering pump, or reducing temperature.")
    elif sizing_results["NPSHA"] < 1.0:
        warnings.append("NPSH_A is very low — risk of cavitation. Consider increasing suction size, lowering pump, or reducing temperature.")

    sizing_results["warnings"] = warnings
    
    msg = (
        f"Fluid: {fluid_props['fluid_name']}\n"
        f"Min Temp: {fluid_props['min_temp_C']} °C, Max Temp: {fluid_props['max_temp_C']} °C\n"
        f"Density @ Min Temp: {density:.2f} kg/m³\n"
        f"Viscosity @ Min Temp: {viscosity:.3f} cP\n"
        f"Vapor Pressure @ Max Temp: {vapor_pressure_kPa:.3f} kPa\n\n"
        f"Total Pressure Drop in Suction Line: {suction_pressure_drop_kPa:.3f} kPa\n"
        f"Total Pressure Drop in Discharge Line: {discharge_pressure_drop_kPa:.3f} kPa\n"
        f"Pump Head Required: {sizing_results['pump_head_m']:.3f} m\n"
        f"Hydraulic Power: {sizing_results['hydraulic_power_kW']:.3f} kW\n"
        f"Brake Power (75% efficiency): {sizing_results['brake_power_kW']:.3f} kW\n"
        f"NPSH_A: {sizing_results['NPSHA']:.3f} m\n"
        f"NPSH_A (Including 1m margin): {sizing_results['NPSHA_margin_included']:.3f} m"
    )

    messagebox.showinfo("Pump Sizing Results", msg)

    if sizing_results.get("warnings"):
        warning_msg = "\nWarnings:\n"
        for w in sizing_results["warnings"]:
            warning_msg += f" - {w}\n"
        messagebox.showwarning("Pump Sizing Warnings", warning_msg)


def on_plot_curves(fluid_props, entries):
    """Handler for plotting curves button"""
    # First validate that basic inputs are filled
    try:
        pump_centreline = float(entries['pump_centreline'].get())
        suction_source = float(entries['suction_source'].get())
        discharge_height = float(entries['discharge_height'].get())
        max_dest_pressure = float(entries['max_dest_pressure'].get())
    except ValueError:
        messagebox.showerror("Input Error", "Please fill in all elevation and pressure fields first")
        return
    
    # Get flow range from user
    dialog = FlowRangeDialog(entries['root'])
    entries['root'].wait_window(dialog)
    
    if not dialog.result:
        return
    
    flow_min, flow_max, num_points = dialog.result
    
    # Calculate vapor pressure
    try:
        fluid_at_max = Chemical(fluid_props["fluid_name"], T=fluid_props["max_temp_C"] + 273.15)
        vapor_pressure_Pa = fluid_at_max.VaporPressure(fluid_props["max_temp_C"] + 273.15)
        vapor_pressure_kPa = vapor_pressure_Pa / 1000
    except Exception:
        vapor_pressure_kPa = 0
    
    # Prepare inputs for curve generation
    total_elevation_diff = discharge_height - suction_source
    suction_elev_diff = suction_source - pump_centreline
    
    other_inputs = {
        "segments_suction": [{
            "length": 50,
            "material": "Carbon Steel",
            "Nom_D": 3,
            "schedule": "40",
        }],
        "segments_discharge": [{
            "length": 150,
            "material": "Carbon Steel",
            "Nom_D": 3,
            "schedule": "40",
        }],
        "suction_elev_diff": suction_elev_diff,
        "total_elevation_diff": total_elevation_diff,
        "max_dest_pressure": max_dest_pressure,
        "efficiency": 0.75,
        "vapor_pressure_kPa": vapor_pressure_kPa,
        "altitude_m": pump_centreline
    }
    
    # Generate curve data
    try:
        results = run_flow_curve(fluid_props, flow_min, flow_max, num_points, other_inputs)
        plot_curve(results, fluid_props["fluid_name"])
    except Exception as e:
        messagebox.showerror("Plotting Error", f"Failed to generate curves: {e}")


# Main Running Script Section
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window initially

    fluid_properties = get_fluid_info(root)

    root.deiconify()
    root.title("Pump Sizing Calculator")

    # Create entry widgets and store references
    entries = {}
    
    tk.Label(root, text="Enter flow rate (m³/h):").grid(row=0, column=0, padx=10, pady=10, sticky='e')
    entries['flow_rate'] = tk.Entry(root)
    entries['flow_rate'].grid(row=0, column=1, padx=10, pady=10)
    
    tk.Label(root, text="Pump Centreline Height (m):").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    entries['pump_centreline'] = tk.Entry(root)
    entries['pump_centreline'].grid(row=1, column=1, padx=10, pady=5)

    tk.Label(root, text="Suction Source Height (m):").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    entries['suction_source'] = tk.Entry(root)
    entries['suction_source'].grid(row=2, column=1, padx=10, pady=5)

    tk.Label(root, text="Discharge Height (m):").grid(row=3, column=0, padx=10, pady=5, sticky='e')
    entries['discharge_height'] = tk.Entry(root)
    entries['discharge_height'].grid(row=3, column=1, padx=10, pady=5)
    
    tk.Label(root, text="Max Required Destination Pressure (kPa):").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    entries['max_dest_pressure'] = tk.Entry(root)
    entries['max_dest_pressure'].grid(row=4, column=1, padx=10, pady=5)
    
    # Store root reference for dialogs
    entries['root'] = root

    # Buttons
    calc_button = tk.Button(root, text="Calculate Pump Size",
                            command=lambda: on_calculate(fluid_properties, entries),
                            bg='lightblue', font=('Arial', 10, 'bold'))
    calc_button.grid(row=5, column=0, columnspan=2, pady=10)
    
    # Add the Plot Curves button
    plot_button = tk.Button(root, text="Generate Performance Curves",
                           command=lambda: on_plot_curves(fluid_properties, entries),
                           bg='lightgreen', font=('Arial', 10, 'bold'))
    plot_button.grid(row=6, column=0, columnspan=2, pady=5)
    
    # Add informational label
    info_label = tk.Label(root, text="Fill in elevation/pressure fields before generating curves",
                         font=('Arial', 8), fg='gray')
    info_label.grid(row=7, column=0, columnspan=2, pady=5)
    
    root.mainloop()