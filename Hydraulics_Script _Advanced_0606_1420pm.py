# This Advanced Hydraulics Script allows the user to automatically size lines for almost all pipe marterials, sizes
# and for almost all common fluids. It uses freely available equations from Crane TPM-410, 2009 Edition
# These equations are generally considered gold standard and conservative
# By Louis Walker, Process Engineer, 2025
# See Read Me Instructions Text File for more informaiton
# These results should not be provided as final without prior checking by an RPEQ Process Engineer
# This should not be reproduced or provided in native form to a client
# Contact: louis.walker110@gmail.com

#---------------------------Import necessary libraries---------------------------------------------------
import tkinter as tk
from tkinter import simpledialog, messagebox
from thermo.chemical import Chemical
# from thermo.vapor_pressure import VaporPressure ---- For now leave this out to make things a little faster
from math import pi, sqrt, log10
from fluids import nearest_pipe, fittings
from AS_4130_HDPE_Capability_Matrix import lookup_hdpe_pipe, AS4130_HDPE
from pipe_data import roughness
#----------------------Define the fluid input class and build the pop up box------------------------------

class FluidInputDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Fluid Name (e.g. water):").grid(row=0, sticky="w")
        tk.Label(master, text="Min Temperature (°C):").grid(row=1, sticky="w")
        tk.Label(master, text="Max Temperature (°C):").grid(row=2, sticky="w")
        tk.Label(master, text="Max Flowrate (m3/hr):").grid(row=3, sticky="w")
        tk.Label(master, text="Maxium Pressure Drop Threshold (kPa/100m) :").grid(row=4, sticky="w")
        tk.Label(master, text="Maximum Fluid Velocity Threshold (m/s):").grid(row=5, sticky="w")

        self.entry_fluid = tk.Entry(master)
        self.entry_min_temp = tk.Entry(master)
        self.entry_max_temp = tk.Entry(master)
        self.entry_max_Q = tk.Entry(master)
        self.entry_p_drop_threshold= tk.Entry(master)
        self.entry_velocity_threshold = tk.Entry(master)

        
        self.entry_fluid.grid(row=0, column=1)
        self.entry_min_temp.grid(row=1, column=1)
        self.entry_max_temp.grid(row=2, column=1)
        self.entry_max_Q.grid(row=3, column=1)
        self.entry_p_drop_threshold.grid(row=4, column=1)
        self.entry_velocity_threshold.grid(row=5, column=1)
        return self.entry_fluid
#----------------------Validate that the user input flowrate, fluid and temperatures as expected------------
    def validate(self):
        fluid_name = self.entry_fluid.get().strip()
        min_temp = self.entry_min_temp.get().strip()
        max_temp = self.entry_max_temp.get().strip()
        max_Q = self.entry_max_Q.get().strip()
        p_drop_threshold = self.entry_p_drop_threshold.get().strip()
        velocity_threshold = self.entry_velocity_threshold.get().strip()
    
    # Check if fluid name is not empty and not a number    
        if not fluid_name or fluid_name.isdigit():
            messagebox.showerror("Input Error", "Fluid name must be a non-empty string (not a numeric value).")
            return False
    # Check if minimum temperature of fluid is not empty and is a number
        try:
            self.min_temp = float(min_temp)
        except ValueError:
            messagebox.showerror("Input Error", "Minimum temperature must be a number.")
            return False
    # Check if maximum temperature of fluid is not empty and is a number
        try:
            self.max_temp = float(max_temp)
        except ValueError:
            messagebox.showerror("Input Error", "Maximum temperature must be a number.")
            return False
    # Check if minimum temperature of fluid is not greater than max temp of fluid (sanity)
        if self.min_temp >= self.max_temp:
            messagebox.showerror("Input Error", "Min temp must be less than max temp.")
            return False
    # Check if flowrate is a valuid number > 0 
        try:
            self.max_Q = float(max_Q)
            if self.max_Q <= 0:
                messagebox.showerror("Input Error", "Max flowrate must be a positive number.")
                return False 
        except ValueError:
            messagebox.showerror("Input Error", "Max flowrate must be a number.")
            return False
    # Check if pressure drop per 100m is reasonable
        try:
            self.p_drop_threshold= float(p_drop_threshold)
            if self.p_drop_threshold<= 0:
                messagebox.showerror("Input Error", "Maxium pressure drop threshold (kPa per 100m) must be a positive number.")
                return False 
        except ValueError:
            messagebox.showerror("Input Error", "Maxium pressure drop threshold (kPa per 100m) must be a number.")
            return False
        try:
            self.velocity_threshold= float(velocity_threshold)
            if self.velocity_threshold<= 0:
                messagebox.showerror("Input Error", "Maxium velocity threshold (m/s) must be a positive number.")
                return False 
        except ValueError:
            messagebox.showerror("Input Error", "Maxium velocity threshold (m/s) must be a number.")
            return False
        self.fluid = fluid_name
        return True
    # Pass values from first pop up to rest of script 
    def apply(self):
        pass
    
#-----------------------------------Defines main class----------------------------------------------
class SegmentLengthsApp(tk.Toplevel):
    def __init__(self, master, num_segments):
        super().__init__(master)
        self.title("Hydraulics Segment Lengths & Elbows")

        self.num_segments = num_segments
        self.data = [["" for _ in range(self.num_segments)] for _ in range(25)]
        self.row_headers = [
            "Segment Length, m",
            "Pipe Material",
            "Nominal Diameter (Inches for Steel, mm for HDPE)",
            "Schedule (e.g. STD or 40) or SDR (e.g. SDR17)",
            "Number of LR 90° elbows",
            "Number of LR 45° elbows",
            "Number of U-bends",
            "Number of tees through branch",
            "Number of tees straight thru",
            "Number of pipe Entrances",
            "Number of Pipe Exits",
            "Number of Std Globe Valves",
            "Number of Y-type Globe Valves",
            "Number of Branch Flow Plug Valves",
            "Number of Gate Valves",
            "Number of Plug Valves Through Branch",
            "Number of Plugs Valves Straight Through",
            "Number of Std Ball Valves-2 port",
            "Number of Std Ball Valves-3 port",
            "Number of Centric BFVs",
            "Number of Double Offset BFVs",
            "Number of Triple Offset BFVs",
            "Number of Swing Type Check Valves",
            "Number of Lift Type Check Valves",
            "Number of Tilting Type Check Valves",
            "User supplied K"
        ]

        container = tk.Frame(self)
        container.pack(padx=10, pady=0, fill=tk.X)

        row_header_frame = tk.Frame(container)
        row_header_frame.pack(side=tk.LEFT, fill=tk.Y, pady=(0, 0))
        # Import the excel style sheet and the fonts
        from tksheet import Sheet
        import tkinter.font as tkfont
        label_font = tkfont.Font(family="Arial", size=10)
        row_height = 25
        total_height = row_height * len(self.row_headers)
        
        # Create the headers for each row, which label what the fitting is etc etc.
        for i, header in enumerate(self.row_headers):
            label = tk.Label(row_header_frame, text=header, anchor="w", width=40, font=label_font)
            if i == 0:
                label.grid(row=i, column=0, sticky="w", padx=10, pady=(25,0))
            else: 
                label.grid(row=i, column=0, sticky="w", padx=10, pady=(0,0))
            label.config(pady=2)
        # Create the sheet where user inputs their fittings data
        self.sheet = Sheet(container,
                    data=self.data,
                    headers=[f"Segment {i+1}" for i in range(self.num_segments)],
                    width=750,
                    height=total_height,
                    row_height = row_height)
        self.sheet.enable_bindings(("single_select", "edit_cell"))
        self.sheet.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Create the submit button, for user to submit their inputs
        self.submit_btn = tk.Button(self, text="Submit", command=self.submit)
        self.submit_btn.pack(pady=5)

        # Readiness flags
        self.lengths_ready = False
        self.materials_ready = False
        self.nom_Ds_ready = False
        self.SCH_ready = False
        self.elbows_ready = False
        self.elbows_45_ready = False
        self.U_bends_ready = False
        self.tee_branch_thrus_ready = False
        self.tee_straight_thrus_ready = False
        self.pipe_entrances_ready = False
        self.pipe_exits_ready = False
        self.std_globe_valve_ready = False
        self.y_type_globe_valve_ready = False
        self.plug_valve_branch_thrus_ready = False
        self.plug_valve_straight_thrus_ready = False
        self.gate_valves_ready = False
        self.std_ball_valves_2port_ready = False
        self.std_ball_valves_3port_ready = False
        self.BFV_centrics_ready = False
        self.BFV_double_offset_ready = False
        self.BFV_triple_offset_ready = False
        self.check_valve_swing_ready = False
        self.check_valve_lift_ready = False
        self.check_valve_tilt_ready = False
        self.user_Ks_ready = False

    #----------------------Functions to get user inputs from the sheet and validate them------------------------
    def get_lengths(self):
        data = self.sheet.get_sheet_data()
        row = data[0]
        lengths = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                messagebox.showwarning("Input Warning", f"Length for Segment {i+1} missing; defaulting to 0.")
                lengths.append(0.0)
                continue
            try:
                fval = float(val)
                if fval <= 0:
                    raise ValueError
                lengths.append(fval)
            except Exception:
                raise ValueError(f"Invalid length for Segment {i+1}: '{val}'")
        return lengths

    def get_material(self):
        data = self.sheet.get_sheet_data()
        row = data[1]
        materials = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                val = "Carbon Steel"
                messagebox.showwarning("Input Warning", f"Material for Segment {i+1} missing; defaulting to Carbon Steel.")
            if val not in ("Carbon Steel", "HDPE", "Stainless Steel"):
                raise ValueError(f"Invalid material at Segment {i+1}: '{val}'")
            materials.append(val)
        return materials

    def get_nom_D(self):
        data = self.sheet.get_sheet_data()
        row = data[2]
        nom_Ds = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                messagebox.showwarning("Input Warning", f"Nominal Diameter for Segment {i+1} missing; defaulting to 0.")
                nom_Ds.append(0.0)
                continue
            try:
                fval = float(val)
                if fval <= 0:
                    raise ValueError
                nom_Ds.append(fval)
            except Exception:
                raise ValueError(f"Invalid Nominal Diameter at Segment {i+1}: '{val}'")
        return nom_Ds

    def get_SCH(self):
        data = self.sheet.get_sheet_data()
        row = data[3]
        schs = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                val = "40"
                messagebox.showwarning("Input Warning", f"Schedule for Segment {i+1} missing; defaulting to '40'.")
            schs.append(val)
        return schs

    def get_int_row(self, row_idx, description, default=0, allow_zero=True):
        data = self.sheet.get_sheet_data()
        row = data[row_idx]
        results = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                results.append(default)
                continue
            try:
                val_int = int(val)
                if not allow_zero and val_int == 0:
                    raise ValueError
                elif val_int < 0:
                    raise ValueError
                results.append(val_int)
            except Exception:
                raise ValueError(f"Invalid number of {description} at Segment {i+1}: '{val}'")
        return results

    def get_elbows(self):
        return self.get_int_row(4, "90° elbows")

    def get_45_elbows(self):
        return self.get_int_row(5, "45° elbows")

    def get_U_bends(self):
        return self.get_int_row(6, "U-bends")

    def get_tee_branches(self):
        return self.get_int_row(7, "tees through branch")

    def get_tee_straight_thrus(self):
        return self.get_int_row(8, "tees straight thru")

    def get_pipe_entrances(self):
        return self.get_int_row(9, "pipe entrances")

    def get_pipe_exits(self):
        return self.get_int_row(10, "pipe exits")

    def get_std_globe_valves(self):
        return self.get_int_row(11, "Standard Globe Valves")

    def get_Y_globe_valves(self):
        return self.get_int_row(12, "Y-type Globe Valves")

    def get_plug_valves_branch_throughs(self):
        return self.get_int_row(13, "Branch Flow Plug Valves")

    def get_plug_valves_straights_throughs(self):
        return self.get_int_row(14, "Straight Through Plug Valves")

    def get_gate_valves(self):
        return self.get_int_row(15, "Gate Valves")

    def get_std_ball_valves(self):
        return self.get_int_row(16, "Std Ball Valves")

    def get_std_ball_valve_3port(self):
        return self.get_int_row(17, "Standard Ball Valve - 3 port")

    def get_BFV_centric(self):
        return self.get_int_row(18, "Butterfly valve centric")

    def get_BFV_double_offset(self):
        return self.get_int_row(19, "Butterfly valve double offset")

    def get_BFV_triple_offset(self):
        return self.get_int_row(20, "Butterfly valve triple offset")
    
    def get_check_valve_swing(self):
        return self.get_int_row(21, "Check Valve Swing")

    def get_check_valve_lift(self):
        return self.get_int_row(22, "Check Valve Lift")

    def get_check_valve_tilt(self):
        return self.get_int_row(23, "Check Valve Tilting")    

    def get_user_Ks(self):
        # Assuming user supplied K must be a float
        data = self.sheet.get_sheet_data()
        row = data[24]  # Adjust row index as per your sheet structure!
        results = []
        for i, val in enumerate(row):
            val = val.strip()
            if val == "":
                results.append(0.0)
                continue
            try:
                val_float = float(val)
                if val_float < 0:
                    raise ValueError
                results.append(val_float)
            except Exception:
                raise ValueError(f"Invalid user supplied K value at Segment {i+1}: '{val}'")
        return results  

    def submit(self):
        try:
            self.focus_set()
            self.update()

            self.lengths = self.get_lengths()
            self.materials = self.get_material()
            self.nom_Ds = self.get_nom_D()
            self.schedule = self.get_SCH()
            self.elbows_90 = self.get_elbows()
            self.elbows_45 = self.get_45_elbows()
            self.u_bends = self.get_U_bends()
            self.tee_branch_thrus = self.get_tee_branches()
            self.tee_straight_thrus = self.get_tee_straight_thrus()
            self.pipe_entrances = self.get_pipe_entrances()
            self.pipe_exits = self.get_pipe_exits()
            self.std_globe_valves = self.get_std_globe_valves()
            self.Y_globes = self.get_Y_globe_valves()
            self.plug_valve_branch_thrus = self.get_plug_valves_branch_throughs()
            self.plug_valve_straight_thrus = self.get_plug_valves_straights_throughs()
            self.gate_valves = self.get_gate_valves()
            self.std_ball_valves_2port = self.get_std_ball_valves()  
            self.std_ball_valves_3port = self.get_std_ball_valve_3port()
            self.BFV_centrics = self.get_BFV_centric()
            self.BFV_double_offset = self.get_BFV_double_offset()
            self.BFV_triple_offset = self.get_BFV_triple_offset()
            self.check_valve_swing = self.get_check_valve_swing()
            self.check_valve_lift = self.get_check_valve_lift()
            self.check_valve_tilt = self.get_check_valve_tilt()
            self.user_Ks = self.get_user_Ks()

            # Allow functions to acutally run
            self.lengths_ready = True
            self.materials_ready = True
            self.nom_Ds_ready = True
            self.SCH_ready = True
            self.elbows_ready = True
            self.elbows_45_ready = True
            self.U_bends_ready = True
            self.tee_branch_thrus_ready = True
            self.tee_straight_thrus_ready = True
            self.pipe_entrances_ready = True
            self.pipe_exits_ready = True
            self.std_globe_valve_ready = True
            self.y_type_globe_valve_ready = True
            self.plug_valve_branch_thrus_ready = True
            self.plug_valve_straight_thrus_ready = True
            self.gate_valves_ready = True
            self.std_ball_valves_2port_ready = True
            self.std_ball_valves_3port_ready = True
            self.BFV_centrics_ready = True
            self.BFV_double_offset_ready = True
            self.BFV_triple_offset_ready = True
            self.check_valve_swing_ready = True
            self.check_valve_lift_ready = True
            self.check_valve_tilt_ready = True
            self.user_Ks_ready = True

            # Retrieve row data
            data = self.sheet.get_sheet_data()
            for i, row in enumerate(data):
                pass  # for possible debug
            # Makes sure to quit program!
            self.quit()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Input Error", str(e))
    def calculate_pressure_drop_for_segment(self, segment, current_nom_D):
            material = segment["material"]
            pipe_length = segment["length"]

            if material.lower() == "hdpe":
                SDR = segment.get("SDR", "SDR17")
                props = lookup_hdpe_pipe(current_nom_D, SDR)
                ID_pipe = props["MeanID"] / 1000
                epsilon = roughness["HDPE"]
            else:
                schedule = segment.get("schedule", "40")
                _, ID_pipe, _, _ = nearest_pipe(NPS=current_nom_D, schedule=schedule)
                epsilon = roughness["Carbon Steel"]

            ID_pipe_val = ID_pipe.magnitude if hasattr(ID_pipe, 'magnitude') else ID_pipe
            velocity = (max_Q / 3600) / (pi / 4 * ID_pipe_val ** 2)
            Re = density * velocity * ID_pipe_val / viscosity

            #---------Calculates moody factor explictly, rather than by Cole-Whitebrook eqn.
            if Re < 2300:
                moody_fac = 64 / Re
            else:
                moody_fac = 1 / (-2 * log10(epsilon / (ID_pipe_val * 1000) / 3.7 + 5.74 / Re ** 0.9))**2

            rhov2 = (density*velocity ** 2) # Caclulates rhov2 
            p_drop_100 = moody_fac * (100 / ID_pipe_val) * (rhov2)/(2*1000) # Explicitly calculates pressure drop per 100 m using the
            # Darcy-Weisbach formula, and explictly setting pipe length to 100m.

            return p_drop_100, moody_fac, current_nom_D, ID_pipe_val, velocity
        
    #----------------------Functions to get HDPE and Carbon Steel Pipe sizes for the user to choose from------------------------
    def get_hdpe_sizes(self):
        return sorted(list(AS4130_HDPE.keys()))

    def get_CS_sizes(self):
        return [0.25,0.5,0.75,1,1.25,1.5,2,2.5,3,3.5,4.0,5.0,6.0,8.0,10.0,12.0,14.0,16.0,18.0,20.0,24.0,30.0]
    def on_optimize(self,):
        # Do any GUI cleanup if needed
        self.optimize_segments(segments, dlg.p_drop_threshold, dlg.velocity_threshold)
        messagebox.showinfo("Optimization Complete", "Pipe sizes have been optimized!\nNow hit the Report Results button if you want to see results.")

    # Create the Tkinter results window with the optimize button
    def show_results_window(self):
        win = tk.Toplevel(root)
        win.title("Results / Actions")

        btn_optimize = tk.Button(win, text="Optimize Pipe Sizes", command=self.on_optimize)
        btn_optimize.pack(pady=10)

        # Optionally add a button to view results (so user runs reporting after optimizing)
        btn_view = tk.Button(win, text="Show Results", command= self.run_main_calculation)
        btn_view.pack(pady=10)

    def calculate_segment_results(self):

        for seg in self.segments:
        # Use current diameter for each segment
            current_nom_D = seg["Nom_D"]
            p_drop_100, moody_fac, Nom_D, ID_pipe_val, velocity = self.calculate_pressure_drop_for_segment(seg, current_nom_D)

        # Store the values in the segment dict
            seg["p_drop_100"] = p_drop_100
            seg["Moody_Factor"] = moody_fac
            seg["Nom_D"] = Nom_D
            seg["ID_pipe_val"] = ID_pipe_val
            seg["Velocity"] = velocity
    # Provide your reporting (reuse your earlier calculation)
    def run_main_calculation(self):
        # This function runs usual calculations and shows results in a messagebox
        self.calculate_segment_results()  # <----- Add this line!
        text = ""
        text += f"Hit OK to continue to final results, otherwise hit Optimize to determine optimal pipe size\n\n"
        for idx, seg in enumerate(segments, start =1):
            # get/store any computed values and build 'text'
            text += f"Segment {idx} size, DN {seg['Nom_D']} (Velocity: {seg.get('Velocity',0):.2f} m/s)\n"
            text += f"Segment {idx} : (Pressure drop per 100 m is: {seg.get('p_drop_100',0):.2f} kPa/100m)\n"       
        messagebox.showinfo("Hydraulic Calculation Results", text)
        self.quit()
        self.destroy()
        
    # Functions to increase and decrease pipe sizes based on pressure drop and velocity norms or
    # thresholds, as required by the user.
    def increase_size(self,current_nom_D, material):
        size_list = self.get_hdpe_sizes() if material.lower() == "hdpe" else sorted(self.get_CS_sizes())
        try:
            current_index = size_list.index(current_nom_D)
            new_size = size_list[current_index + 1]
            return new_size
        except IndexError:
            print(f"Already at max size: {current_nom_D}")
        return current_nom_D

    def decrease_size(self,current_nom_D, material):
        if material.lower() == "hdpe":
            all_sizes_hdpe = sorted(self.get_hdpe_sizes())
            size_list = all_sizes_hdpe
        else: 
            all_sizes_carbon_steel = self.get_CS_sizes()
            size_list = all_sizes_carbon_steel
        try:
            new_size = size_list[size_list.index(current_nom_D) -1]
            return new_size 
        except ValueError:
            print(f"Already at min size: {current_nom_D}")
            return current_nom_D
    def optimize_segments(self,segments, p_drop_threshold, velocity_threshold):
        for i, seg in enumerate(segments):
            current_nom_D = seg["Nom_D"]  # Start with provided Nom_D
            acceptable_drop = False
            material = seg["material"]
            
            
            while not acceptable_drop:
                p_drop_100, moody_fac, Nom_D, ID_pipe_val,velocity = self.calculate_pressure_drop_for_segment(seg, current_nom_D)      
                velocity = (max_Q / 3600) / (pi / 4 * ID_pipe_val ** 2)

                threshold_min_P = 10 # Set minimum pressure drop (kPa/100m) as 10
 
                if p_drop_100 > p_drop_threshold or velocity > velocity_threshold:
                    current_nom_D = self.increase_size(current_nom_D, material)
                elif p_drop_100 < threshold_min_P:
                    prev_nom_D_bigger = current_nom_D
                    current_nom_D = self.decrease_size(current_nom_D, material)
                    #Recalculates the pressure drop and velocity at the smaller size

                    p_drop_small, moody_fac_small, Nom_D_small, ID_pipe_val_small, velocity_small = self.calculate_pressure_drop_for_segment(seg, current_nom_D)

                    if (p_drop_small > p_drop_threshold or velocity_small > velocity_threshold):
                        # Can't go down a size so revert to prevous size
                            current_nom_D = prev_nom_D_bigger
                            moody_fac = moody_fac_small
                            acceptable_drop = True

                else:
                    acceptable_drop = True
            
            # Always calculate results for current_nom_D, which is the accepted optimal size
            p_drop_100, moody_fac, Nom_D, ID_pipe_val, velocity = self.calculate_pressure_drop_for_segment(seg, current_nom_D)

            seg["Nom_D"] = current_nom_D
            seg["ID_Used"] = ID_pipe_val
            seg["pressure_drop_100"] = p_drop_100
            seg["Velocity"] = velocity
            seg["Moody Factor"] = moody_fac

# ------------------------------- Main Script Block ---------------------------------
# This is the main script block that runs when the script is executed
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    dlg = FluidInputDialog(root, title="Enter fluid properties")
    if not hasattr(dlg, "fluid"):
        messagebox.showinfo("Info", "User cancelled fluid input. Exiting.")
        root.destroy()
        exit()
    # Pull through temperatures, fluid name and flowrate from user input
    fluid_name = dlg.fluid
    norm_pump_temp = dlg.min_temp
    max_pump_temp = dlg.max_temp
    max_Q = dlg.max_Q
    print(f"Fluid: {fluid_name}")
    print(f"Min Temp: {norm_pump_temp}")
    print(f"Max Temp: {max_pump_temp}")

    temp_min_K = norm_pump_temp + 273.15
    temp_max_K = max_pump_temp + 273.15

    try:
        fluid_at_min = Chemical(fluid_name, T=temp_min_K)
        fluid_at_max = Chemical(fluid_name, T=temp_max_K)

        density = fluid_at_min.rho
        viscosity = fluid_at_min.mu
        vapor_pressure = fluid_at_max.VaporPressure(temp_max_K)
        boiling_point_K = fluid_at_min.Tb
        boiling_point_C = boiling_point_K - 273.15
        if temp_max_K > boiling_point_K:
            proceed = messagebox.askyesno(
        "Fluid Temperature Warning",
        f"WARNING: Maximum fluid temperature {max_pump_temp:.2f} °C exceeds boiling point of {fluid_name}, {boiling_point_C:.2f} °C, at atmospheric pressure.\n\n"
        "Please VERIFY the actual boiling point at your system's operating pressure before proceeding.\n\n"
        "Click YES ONLY IF you have confirmed the fluid will NOT boil under operating conditions. Otherwise click NO to cancel and review inputs."
        )
            if not proceed:
        # User chose not to disregard - stop execution or exit
                root.destroy()   # Close main window
                exit()
        print(f"Density of {fluid_name} at {norm_pump_temp}°C: {density:.2f} kg/m³")
        print(f"Viscosity of {fluid_name} at {norm_pump_temp}°C: {viscosity*1000:.2f} cP")
    except Exception as e:
        messagebox.showerror("Fluid properties error", f"Could not obtain properties for {fluid_name}: {str(e)}")
        root.destroy()
        exit()   
    # Get number of segments before creating sheet
    num_segments = simpledialog.askinteger("Input", "How many segments do you want?", minvalue=1, maxvalue=100, parent=root)

    if num_segments is None:
        messagebox.showinfo("Info", "User cancelled segment count input. Exiting.")
        root.destroy()
        exit()

    # Launch segment length input GUI
    app = SegmentLengthsApp(root, num_segments)
    app.mainloop()

    if not app.lengths_ready:
        messagebox.showinfo("Info", "User cancelled segment data input. Exiting.")
        root.destroy()
        exit()

#---------------------Build segments list with all data ready for calculation and append data------------------------
    segments = []
    for i in range(num_segments):
        segment = {
            "length": app.lengths[i] if i < len(app.lengths) else 0,
            "material": app.materials[i] if i < len(app.materials) else "HDPE",
            "Nom_D": app.nom_Ds[i] if i < len(app.nom_Ds) else 0,
            "schedule": app.schedule[i] if i < len(app.schedule) else "40",
            "elbows_90": app.elbows_90[i] if i < len(app.elbows_90) else 0,
            "elbows_45": app.elbows_45[i] if i < len(app.elbows_45) else 0,
            "U-bends": app.u_bends[i] if i < len(app.u_bends) else 0,
            "Tees through branch": app.tee_branch_thrus[i] if i < len(app.tee_branch_thrus) else 0,
            "Tees run thru": app.tee_straight_thrus[i] if i < len(app.tee_straight_thrus) else 0,
            "Pipe Entrances": app.pipe_entrances[i] if i < len(app.pipe_entrances) else 0,
            "Pipe Exits": app.pipe_exits[i] if i < len(app.pipe_exits) else 0,
            "Std Globe Valve": app.std_globe_valves[i] if i < len(app.std_globe_valves) else 0,
            "Y type Globe Valve": app.Y_globes[i] if i < len(app.Y_globes) else 0,
            "Plug Valve through branch": app.plug_valve_branch_thrus[i] if i < len(app.plug_valve_branch_thrus) else 0,
            "Plug Valve run thru": app.plug_valve_straight_thrus[i] if i < len(app.plug_valve_straight_thrus) else 0,
            "Gate Valve": app.gate_valves[i] if i < len(app.gate_valves) else 0,
            "Std Ball Valve-2 port": app.std_ball_valves_2port[i] if i < len(app.std_ball_valves_2port) else 0,
            "Std Ball Valve-3 port": app.std_ball_valves_3port[i] if i < len(app.std_ball_valves_3port) else 0,
            "Butterfly valve centric": app.BFV_centrics[i] if i < len(app.BFV_centrics) else 0,
            "Butterfly valve double offset": app.BFV_double_offset[i] if i < len(app.BFV_double_offset) else 0,
            "Butterfly valve triple offset": app.BFV_triple_offset[i] if i < len(app.BFV_triple_offset) else 0,
            "Check Valve Swing": app.check_valve_swing[i] if i < len(app.check_valve_swing) else 0,
            "Check Valve Lift": app.check_valve_lift[i] if i < len(app.check_valve_lift) else 0,
            "Check Valve Tilting": app.check_valve_tilt[i] if i < len(app.check_valve_tilt) else 0,
            "User supplied K": app.user_Ks[i] if i < len(app.user_Ks) else 0,
            

        }
        segments.append(segment)
        app.segments = segments
    app.show_results_window()
    root.mainloop()
    
    # Initialise arrays and some key parameters
    Q_m3hr = max_Q
    sum_of_pressure_drop = 0
    pressure_drop_segments = []
    previous_diameter = None
    previous_NPS = None

#----------------------------- Loop through all segments and calculate relevant variables---------------------------------
    for i ,seg in enumerate(segments):
        p_drop_100, moody_fac, Nom_D, ID_pipe_val, velocity = app.calculate_pressure_drop_for_segment(seg, seg["Nom_D"])
        current_nom_D = Nom_D
        Ero_C = 100
        Ero_v_imp = Ero_C / sqrt(0.062428 * density)
        Ero_v_SI = Ero_v_imp / 3.28083989
        rhov2 = density*(velocity**2)
        rhov2_g = (velocity ** 2) / (2 * 9.81)
        material = seg["material"]
        pipe_length = seg["length"]
        num_pipe_entrances = seg["Pipe Entrances"]
        num_pipe_exits = seg["Pipe Exits"]
        num_90_elbows = seg["elbows_90"]
        num_45_elbows = seg["elbows_45"]
        num_U_bends = seg["U-bends"]
        num_tees_branch = seg["Tees through branch"]
        num_tees_thru = seg["Tees run thru"]
        num_globe_valve = seg["Std Globe Valve"]
        num_Yglobe_valve = seg["Y type Globe Valve"]
        num_plug_branch = seg["Plug Valve through branch"]
        num_plug_thru = seg["Plug Valve run thru"]
        num_gate_valve = seg["Gate Valve"]
        num_std_ball = seg["Std Ball Valve-2 port"]
        num_ball_3port = seg["Std Ball Valve-3 port"]
        num_BFV_centric = seg["Butterfly valve centric"]
        num_BFV_do = seg["Butterfly valve double offset"]
        num_BFV_to = seg["Butterfly valve triple offset"]
        num_check_valve_swing = seg["Check Valve Swing"]
        num_check_valve_lift = seg["Check Valve Lift"]
        num_check_valve_tilt = seg["Check Valve Tilting"]

        user_K = seg["User supplied K"]

        D_use = ID_pipe_val
#----------------------Computes K-values for all valves and fittings based on Crane TPM-410,2009, A-26 to A-29---------------
        k_elbows = num_90_elbows * 14 * moody_fac   # From Crane TPM-410, 2009, Page A-30 - For Long Radius Elbows where r/D = 1.5
        k_45_elbows = num_45_elbows * 16 * moody_fac # From Crane TPM-410, 2009, Page A-30 - For Std. 45 deg. elbows
        k_u_bends = num_U_bends * 50 * moody_fac # From Crane TPM-410, 2009, Page A-30
        k_tee_branch = num_tees_branch * 60 * moody_fac # From Crane TPM-410, 2009, Page A-30 
        k_tee_thru = num_tees_thru * 20 * moody_fac # From Crane TPM-410, 2009, Page A-30

        k_std_globe = num_globe_valve * fittings.K_globe_valve_Crane(D1=D_use, D2=D_use,fd=moody_fac)
        k_Y_globe = 0
        k_plug_branch_valve = num_plug_branch*fittings.K_plug_valve_Crane(D1=D_use, D2=D_use, angle= 180, style= 2)
        k_plug_straight_valve = num_plug_thru*fittings.K_plug_valve_Crane(D1=D_use, D2=D_use,angle = 180, style= 1)
        k_std_ball = num_std_ball * fittings.K_ball_valve_Crane(D1=D_use, D2=D_use, angle=180)
        k_3_port_ball = num_ball_3port*0.3

        k_BFV_c = num_BFV_centric * fittings.K_butterfly_valve_Crane(D_use, fd=moody_fac, style=0)
        k_BFV_do = num_BFV_do * fittings.K_butterfly_valve_Crane(D_use, fd=moody_fac, style=1)
        k_BFV_to = num_BFV_to * fittings.K_butterfly_valve_Crane(D_use, fd=moody_fac, style=2)

        k_check_valve_swing =num_check_valve_swing*fittings.K_swing_check_valve_Crane(D_use)
        k_check_valve_lift = num_check_valve_lift*fittings.K_lift_check_valve_Crane(D1=(D_use*0.5),D2 = D_use) # K value associated with check valve lift type
        # From Crane TPM-410, 2009, Page A-28. Assumes that seat of lifting valve is approx half the bore of pipe internal diameter
        k_check_valve_tilt = num_check_valve_tilt*fittings.K_tilting_disk_check_valve_Crane(D_use,15)

        k_pipe_entrance = fittings.entrance_sharp(method='Crane') * num_pipe_entrances
        k_pipe_exit = fittings.exit_normal() * num_pipe_exits
        k_user_sup = user_K

        fittings_k_values = [
            k_elbows,
            k_45_elbows,
            k_u_bends,
            k_tee_branch,
            k_tee_thru,
            k_std_globe,
            #k_Y_globe,
            k_plug_branch_valve,
            k_plug_straight_valve,
            k_3_port_ball,
            k_std_ball,
            k_BFV_c,
            k_BFV_do,
            k_BFV_to,
            k_check_valve_swing,
            k_check_valve_lift,
            k_check_valve_tilt,

        ]

        k_fittings_total = sum(fittings_k_values)
        k_pipe_length = moody_fac * pipe_length / D_use
        k_ent_exit = (k_pipe_entrance + k_pipe_exit)
        p_drop_ent_exit = k_ent_exit * rhov2 / (2 * 1000)
        k_factor = moody_fac * (pipe_length / ID_pipe_val)
        p_drop_pipe = k_pipe_length * (rhov2) /(2 * 1000)
        p_drop_fittings = k_fittings_total * rhov2 / 2 / 1000

        p_drop_user_k = k_user_sup * rhov2 / 2 / 1000

        k_total = k_fittings_total + k_ent_exit + k_pipe_length
        p_drop_pf = p_drop_pipe + p_drop_ent_exit + p_drop_fittings +p_drop_user_k
        sum_of_pressure_drop += p_drop_pf
        pressure_drop_segments.append(p_drop_pf)

        # Finds a similar NPS for HDPE as reducer table works primarily for Steel
        # For example ID 96 mm HDPE has an NPS of 4"
        if material.lower() == "hdpe" :
            ID_pipe = ID_pipe_val
            NPS, _, _, _= nearest_pipe(Di = ID_pipe, schedule= '40')
        else:
            ID_pipe = ID_pipe_val
            NPS = current_nom_D
        
        # Calculate the pressure drop associated with each reducer
        # First calculate the length of the reducer based on ASME B13.9 Concentric Reducer Tables
        if previous_diameter is not None and ID_pipe is not None:
            # Import reducer data
            from ASME_Concentric_Reducers_table import reducer_lengths_dict
            larger_nps = float(max(previous_NPS, NPS))
            smaller_nps = float(min(previous_NPS, NPS))
            velocity_max_reducer = (Q_m3hr/3600) / (pi/4*min((previous_diameter),(ID_pipe))**2)
            length_reducer = reducer_lengths_dict.get((larger_nps, smaller_nps), None)

            if length_reducer is None:
                length_reducer_m = None
            else:
                length_reducer_m = length_reducer/1000
            if length_reducer_m is not None:
                K_reducer = fittings.contraction_conical_Crane(
                    Di1=previous_diameter, Di2=ID_pipe, l= length_reducer_m
                )
                p_drop_reducer = K_reducer * (density * velocity_max_reducer**2) / 2 / 1000
                print(
                    f"Reducer between segment {i} and {i+1}: K={K_reducer:.3f}, Pressure drop={p_drop_reducer:.3f} kPa"
                )
                sum_of_pressure_drop += p_drop_reducer
            else:
                print(f"No data for reducer {larger_nps} x {smaller_nps}")
        
        # Store data at the end of the loop
        previous_diameter = ID_pipe
        previous_NPS = NPS
        ID_mm = ID_pipe*1000 # Converts the ID of the pipe into mm, to provide to user (for info only)
        material_prev = material
        seg['pipe_p_drop'] = p_drop_pipe
        seg['fittings_p_drop'] = p_drop_fittings
        seg['K_total'] = k_total
        seg['ID_mm'] = ID_mm
        seg['Total Pressure Drop'] = p_drop_pf
    
#------At the very end of main scrip, after all calculations, create the message box that provides the user the results--------------
    result_text = ""
    for i, seg in enumerate(segments):
        result_text += f"Segment {i+1} (DN {seg['Nom_D']} : ID = {seg.get('ID_mm',0)} mm)\n"
        result_text += f"  - Total pressure drop in segment {i+1} is {seg.get('Total Pressure Drop',0):.2f} kPa\n"
        result_text += f"  - velocity: {seg.get('Velocity',0):.2f} m/s\n"
        result_text += f"  - Unitless pressure drop is {seg.get('pressure_drop_100', 0.0):.2f} kPa/100m\n"
        result_text += f"  - Pressure drop associated with pipe only is {seg.get('pipe_p_drop',0):.2f} kPa\n"
        #result_text += f"  - Total K for all Pipes and Fittings: {seg.get('K_total',0):.2f}\n"
        result_text += f"  - Pressure drop associated with fittings is {seg.get('fittings_p_drop',0):.2f} kPa\n"       
        # Add reducers if you saved this info per-segment
        # result_text += f"  - reducer loss: {seg.get('p_drop_reducer',0):.2f} kPa\n"
    result_text += f"\nTotal pressure drop: {sum_of_pressure_drop:.2f} kPa"
    messagebox.showinfo("Full Hydraulic Segment Results", result_text)
    root.destroy()

