# Hydraulics Script Advanced Core Working 
# Built by Louis Walker, Process Engineer, 2025
# This script takes only the core working code from the advanced hydraulics program
# It removes all inputs and pop_ups and is a standalone function


#------------Import key modules and programs--------------------
from thermo.chemical import Chemical
from thermo.vapor_pressure import VaporPressure
from math import pi, sqrt, log10
from fluids import nearest_pipe, fittings
from AS_4130_HDPE_Capability_Matrix import lookup_hdpe_pipe, AS4130_HDPE
from pipe_data import roughness
from ASME_Concentric_Reducers_table import reducer_lengths_dict


def calculate_pressure_drop(segments, density, viscosity, flow_rate_m3hr):
    Q_m3hr = flow_rate_m3hr
    g = 9.81

    sum_of_pressure_drop = 0.0
    pressure_drop_segments = []
    detailed_results = []
    p_drop_per_100_work = []
    segments_info = []
    previous_diameter = None
    previous_NPS = None

    for i, seg in enumerate(segments, start=1):
        # Set defaults for missing properties to prevent KeyError
        material = seg.get("material", "Carbon Steel")
        Nom_D = seg.get("Nom_D", 0.0)
        pipe_length = seg.get("length", 0.0)
        SDR = seg.get("SDR", "SDR17")
        schedule = seg.get("schedule", "40")

        # Fittings numbers - default zero
        num_pipe_entrances = seg.get("Pipe Entrances", 0)
        num_pipe_exits = seg.get("Pipe Exits", 0)
        num_90_elbows = seg.get("elbows_90", 0)
        num_45_elbows = seg.get("elbows_45", 0)
        num_U_bends = seg.get("U-bends", 0)
        num_tees_branch = seg.get("Tees through branch", 0)
        num_tees_thru = seg.get("Tees run thru", 0)
        num_globe_valve = seg.get("Std Globe Valve", 0)
        num_Yglobe_valve = seg.get("Y type Globe Valve", 0)  # currently unused
        num_plug_branch = seg.get("Plug Valve through branch", 0)
        num_plug_thru = seg.get("Plug Valve run thru", 0)
        num_gate_valve = seg.get("Gate Valve", 0)
        num_std_ball = seg.get("Std Ball Valve-2 port", 0)
        num_ball_3port = seg.get("Std Ball Valve-3 port", 0)
        num_BFV_centric = seg.get("Butterfly valve centric", 0)
        num_BFV_do = seg.get("Butterfly valve double offset", 0)
        num_BFV_to = seg.get("Butterfly valve triple offset", 0)
        num_check__valve_swing = seg.get("Number of Swing Type Check Valves",0)
        num_check__valve_lift = seg.get("Number of Lift Type Check Valves",0)
        num_check__valve_tilting = seg.get("Number of Tilting Type Check Valves",0)
        user_K = seg.get("User supplied K", 0.0)

        # Pipe internal diameter and roughness
        if material.lower() == "hdpe":
            props = lookup_hdpe_pipe(Nom_D, SDR)
            ID_pipe = props["MeanID"] / 1000  # m
            wall_thickness = props["MinWall"]/1000 # pipe wall thickness in m
            epsilon = roughness["HDPE"]
            do_for_red = Nom_D / 1000
            NPS_tuple = nearest_pipe(Do=do_for_red, schedule=40)
            NPS = NPS_tuple[0]
        else:
            NPS, ID_pipe, Do_pipe, t = nearest_pipe(NPS=Nom_D, schedule=schedule)
            ID_pipe = ID_pipe.magnitude if hasattr(ID_pipe, 'magnitude') else ID_pipe
            epsilon = roughness["Carbon Steel"]
            wall_thickness = t # Wall thickness, already in m 
        ID_pipe_val = ID_pipe
        wall_thickness_val = wall_thickness
        # Calculate velocity (m/s)
        area = pi / 4 * ID_pipe_val ** 2
        velocity = (Q_m3hr / 3600) / area 
        print(ID_pipe_val)
        print(epsilon)
        # Reynolds number
        Re = density * velocity * ID_pipe_val / (viscosity/1000) if viscosity > 0 else 0.0
        # Determine friction factor (moody_fac)
        if Re < 2300 and Re > 0:
            regime = "Laminar"
            moody_fac = 64 / Re
        elif 2300 <= Re < 4000:
            regime = "Transitional"
            moody_fac = 0.02  # Approximate placeholder
        else:
            regime = "Turbulent"
            if velocity > 0 and ID_pipe_val > 0:
                moody_fac = 1 / (-2 * log10(epsilon / (ID_pipe_val*1000) / 3.7 + 5.74 / Re ** 0.9))**2
            else:
                moody_fac = 0.02  # fallback
        rhov2 = density * velocity ** 2
        rhov2_g = velocity ** 2 / (2 * g)

        # Straight pipe pressure drop (Darcy-Weisbach)
        p_drop_per_100  = moody_fac * (100 / ID_pipe_val) * (rhov2 / 2) / 1000  # kPa per 100m
        p_drop_pipe = moody_fac * (pipe_length / ID_pipe_val) * (rhov2 / 2) / 1000  # kPa
        # Calculate fittings K values
        k_elbows = num_90_elbows * 14 * moody_fac
        k_45_elbows = num_45_elbows * 16 * moody_fac
        k_u_bends = num_U_bends * 50 * moody_fac
        k_tee_branch = num_tees_branch * 60 * moody_fac
        k_tee_thru = num_tees_thru * 20 * moody_fac

        k_std_globe = num_globe_valve * fittings.K_globe_valve_Crane(D1=ID_pipe_val, D2=ID_pipe_val, fd=moody_fac)
        k_plug_branch_valve = num_plug_branch * fittings.K_plug_valve_Crane(D1=ID_pipe_val, D2=ID_pipe_val, angle=180, style=2)
        k_plug_straight_valve = num_plug_thru * fittings.K_plug_valve_Crane(D1=ID_pipe_val, D2=ID_pipe_val, angle=180, style=1)
        k_std_ball = num_std_ball * fittings.K_ball_valve_Crane(D1=ID_pipe_val, D2=ID_pipe_val, angle=180)
        k_3_port_ball = num_ball_3port * 0.3  # Approximate max loss

        k_BFV_c = num_BFV_centric * fittings.K_butterfly_valve_Crane(ID_pipe_val, fd=moody_fac, style=0)
        k_BFV_do = num_BFV_do * fittings.K_butterfly_valve_Crane(ID_pipe_val, fd=moody_fac, style=1)
        k_BFV_to = num_BFV_to * fittings.K_butterfly_valve_Crane(ID_pipe_val, fd=moody_fac, style=2)

        k_pipe_entrance = fittings.entrance_sharp(method='Crane') * num_pipe_entrances
        k_pipe_exit = fittings.exit_normal() * num_pipe_exits
        k_user_sup = user_K

        # Total fitting K
        k_fittings_total = sum([
            k_elbows, k_45_elbows, k_u_bends, k_tee_branch, k_tee_thru,
            k_std_globe, k_plug_branch_valve, k_plug_straight_valve,
            k_3_port_ball, k_std_ball, k_BFV_c, k_BFV_do, k_BFV_to
        ])

        # Pressure drops for fittings, entrances, exits, user supplied K
        p_drop_fittings = k_fittings_total * rhov2 / 2 / 1000  # kPa
        p_drop_ent_exit = (k_pipe_entrance + k_pipe_exit) * rhov2 / 2 / 1000
        p_drop_user_k = k_user_sup * rhov2 / 2 / 1000

        # Total pressure drop for segment
        p_drop_pf = p_drop_pipe + p_drop_ent_exit + p_drop_fittings + p_drop_user_k

        # Add reducer loss if not first segment
        p_drop_reducer = 0.0
        if previous_diameter is not None and ID_pipe_val is not None:
            larger_nps = max(previous_NPS, NPS)
            smaller_nps = min(previous_NPS, NPS)
            velocity_max_reducer = (Q_m3hr / 3600) / (pi / 4 * min(previous_diameter, ID_pipe_val) ** 2)
            length_reducer = reducer_lengths_dict.get((larger_nps, smaller_nps), None)
            if length_reducer is not None:
                length_reducer_m = length_reducer / 1000
                K_reducer = fittings.contraction_conical_Crane(Di1=previous_diameter, Di2=ID_pipe_val, l=length_reducer_m)
                p_drop_reducer = K_reducer * density * velocity_max_reducer ** 2 / 2 / 1000
                # Add reducer loss to segment and sum
                p_drop_pf += p_drop_reducer
            else:
                # No reducer data available
                pass

        sum_of_pressure_drop += p_drop_pf
        pressure_drop_segments.append(p_drop_pf)
        p_drop_per_100_work.append(p_drop_per_100)
        # Store previous for next iteration
        previous_diameter = ID_pipe_val
        previous_NPS = NPS

        # Save all intermediate data for this segment
    # Save all key geometry & loss data for this segment
        segments_info.append({
            "segment_index": i,
            "length_m": pipe_length,
            "material": material,
            "Nom_D": Nom_D,
            "schedule": schedule,
            "pipe_id_m": ID_pipe_val,
            "wall_thickness_m": wall_thickness_val,
            "pressure_drop_kPa": p_drop_pf,
        })

    return {
        "segments": segments_info,
        "pressure_drop_per_segment_kPa": pressure_drop_segments,
        "total_pressure_drop_kPa": sum_of_pressure_drop,
        "segments_detailed_results": detailed_results,  # optional, more advanced info
        "Pressure Drop Per 100m": p_drop_per_100_work,
    }

# Test Segment located here. User can check vs verified values using this segment
# Simply uncomment (remove triple ''' from start and end of code block) and change required inputs to desired

if __name__ == "__main__":
    # Test with one HDPE segment, SDR17, DN110, and 10 elbows
    test_segments = [{
        "length": 100,                # meters
        "material": "HDPE",
        "Nom_D": 110,                 # nominal diameter in mm for HDPE
        "SDR": "SDR17",
        "elbows_90": 10,              # 10 elbows at 90 degrees
        # All other valves and fittings default to 0
    }]

    # Example fluid properties (water at ~20°C)
    density = 998.2      # kg/m3
    viscosity = 0.00102  # cP 

    flow_rate_m3hr = 100

    results = calculate_pressure_drop(test_segments, density, viscosity, flow_rate_m3hr)

    print("\nFinal Results:")
    print(f"Total pressure drop: {results['total_pressure_drop_kPa']:.3f} kPa")

    # Pressure drop per segment
    for i, val in enumerate(results['pressure_drop_per_segment_kPa'], start=1):
        print(f"Pressure drop for segment {i} is {val:.3f} kPa")

    # Pressure drop per 100m per segment
    # (Make sure your key matches your results dictionary!)
    key_100m = 'Pressure Drop Per 100m'
    val_100m = results[key_100m]

    # Since 'Pressure Drop Per 100m' is now one float per segment, 
    # if it's a list, loop; if single float, just print:
    if isinstance(val_100m, list):
        for i, val in enumerate(val_100m, start=1):
            print(f"Pressure drop per 100m in segment {i} is {val:.3f} kPa/100m")
    else:
        print(f"Pressure drop per 100m in segment 1 is {val_100m:.3f} kPa/100m")