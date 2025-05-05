from flask import Flask, render_template, request
import pandas as pd
import joblib
import numpy as np
import Adafruit_DHT
import platform
import firebase_admin
from firebase_admin import credentials, db
import os
import base64
import json

# Initialize Firebase only once
if not firebase_admin._apps:
    firebase_key_base64 = os.environ.get('FIREBASE_CREDENTIALS')

    if not firebase_key_base64:
        raise ValueError("FIREBASE_CREDENTIALS environment variable is not set or is empty.")

    try:
        firebase_key = json.loads(base64.b64decode(firebase_key_base64).decode('utf-8'))
    except Exception as e:
        raise ValueError(f"Failed to decode FIREBASE_CREDENTIALS: {e}")

    cred = credentials.Certificate(firebase_key)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://smartpolyhouse7-default-rtdb.firebaseio.com/'  # Replace with your actual database URL
    })

app = Flask(__name__)

# Load models
irrigation_model = joblib.load("irrigation_model.pkl")
fertigation_model = joblib.load("random_forest_model.pkl")  # optional, example

# Dataset for plant details
df = pd.read_csv("polyhouse_fertigation_dataset.csv", encoding='latin1')
plant_names = df["Plant_Name"].unique()

motor_flow_rates = {
    "peristaltic": 2.0,
    "centrifugal": 10.0,
    "diaphragm": 5.0
}

# Define constant soil moisture value
soil_moisture = 30  # Example value, change as needed

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error_message = None

    if request.method == "POST":
        try:
            plant_name = request.form["plant_name"]
            current_n = float(request.form["current_n"])
            current_p = float(request.form["current_p"])
            current_k = float(request.form["current_k"])
            area_unit = request.form["area_unit"]
            area_value = float(request.form["area_value"])
            motor_type = request.form["motor_type"].lower()

            plant_data = df[df["Plant_Name"] == plant_name].iloc[0]
            temp_range = plant_data["Temperature_Range(°C)"]
            humid_range = plant_data["Humidity_Range(%)"]
            npk_required = list(map(int, plant_data["NPK_Required(mg/kg)"].split('-')))
            fertilizer_type = plant_data["Fertilizer_Used"]
            fertilizer_bags_per_ha = plant_data["Fertilizer_Bags_per_ha"]
            fertilizer_bags_per_acre = plant_data["Fertilizer_Bags_per_acre"]
            fertilizer_bags_per_sqm = plant_data["Fertilizer_Bags_per_sqm"]

            ideal_temp = sum(map(int, temp_range.split("-"))) / 2
            ideal_humid = sum(map(int, humid_range.split("-"))) / 2

            # Conditional check for Raspberry Pi platform
            if platform.system() == "Linux" and "raspberrypi" in platform.node().lower():
                # Raspberry Pi-specific code
                sensor = Adafruit_DHT.DHT11
                gpio_pin = 4  # Use your actual GPIO pin here

                humidity, temperature = Adafruit_DHT.read_retry(sensor, gpio_pin)

                # Check if sensor read was successful
                if humidity is not None and temperature is not None:
                    sensor_temp = temperature
                    sensor_humid = humidity
                else:
                    sensor_temp = 32  # fallback
                    sensor_humid = 65
            else:
                # Fallback mock values for non-Raspberry Pi platforms
                sensor_temp = 32  # Example fallback value
                sensor_humid = 65  # Example fallback value

            # Upload to Firebase
            try:
                ref = db.reference('/sensor_data')
                ref.push({
                    "temperature": sensor_temp,
                    "humidity": sensor_humid,
                    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                print("Firebase upload success.")
            except Exception as firebase_error:
                print("Firebase upload error:", firebase_error)
                
            temp_error = ideal_temp - sensor_temp
            humidity_error = ideal_humid - sensor_humid

            # Fertigation Calculation (manual or ML)
            req_n = max(npk_required[0] - current_n, 0)
            req_p = max(npk_required[1] - current_p, 0)
            req_k = max(npk_required[2] - current_k, 0)
            max_req_npk = max(req_n, req_p, req_k)
            max_npk_required = max(npk_required)
            motor_flow_rate = motor_flow_rates.get(motor_type, 0)

            if area_unit == "hectares":
                total_bags = round((max_req_npk / max_npk_required) * fertilizer_bags_per_ha * area_value)
            elif area_unit == "acre":
                total_bags = round((max_req_npk / max_npk_required) * fertilizer_bags_per_acre * area_value)
            elif area_unit == "square meter":
                total_bags = round((max_req_npk / max_npk_required) * fertilizer_bags_per_sqm * area_value)
            else:
                total_bags = 0

            water_required = total_bags * 10
            total_solution_volume = water_required + (total_bags * 50)
            time_required = total_solution_volume / motor_flow_rate if motor_flow_rate else 0

            # Run irrigation model
            irrigation_input = np.array([[humidity_error, temp_error, soil_moisture]])
            irrigation_percent = irrigation_model.predict(irrigation_input)[0]

            # OPTIONAL: Run fertigation model if you have it
            fertigation_input = np.array([[current_n, current_p, current_k, area_value]])
            fertigation_dose = fertigation_model.predict(fertigation_input)[0]  # assume output is bag count

            result = {
                "plant_name": plant_name,
                "temp_range": temp_range,
                "humid_range": humid_range,
                "npk_required": npk_required,
                "fertilizer_type": fertilizer_type,
                "required_npk": [req_n, req_p, req_k],
                "total_bags": total_bags,
                "water_required": water_required,
                "solution_volume": total_solution_volume,
                "time_required": round(time_required, 2),
                "motor_type": motor_type,
                "motor_rate": motor_flow_rate,
                "area_unit": area_unit,
                "area_value": area_value,
                "sensor_temp": sensor_temp,
                "sensor_humid": sensor_humid,
                "temp_error": round(temp_error, 2),
                "humidity_error": round(humidity_error, 2),
                "irrigation_percent": round(irrigation_percent, 2),
                "fertigation_dose": round(fertigation_dose, 2)
            }

        except Exception as e:
            error_message = f"Error: {str(e)}"

    return render_template("index.html", plant_names=plant_names,
                           result=result, error_message=error_message)

if __name__ == "__main__":
    app.run(debug=True)
