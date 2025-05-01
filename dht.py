import time
import board
import adafruit_dht

# User input for required temperature and humidity
required_temp = float(input("Enter required temperature (°C): "))
required_humidity = float(input("Enter required humidity (%): "))

# Set a constant soil moisture value (can be replaced with sensor data later)
soil_moisture = 60  # Example constant value

# Set up DHT11 sensor on GPIO4
dhtDevice = adafruit_dht.DHT11(board.D4)

while True:
    try:
        # Get current sensor readings
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity

        # Calculate errors
        temp_error = required_temp - temperature_c
        humidity_error = required_humidity - humidity

        # Display results
        print(f"\nCurrent Readings → Temperature: {temperature_c}°C, Humidity: {humidity}%")
        print(f"Temperature Error: {temp_error}")
        print(f"Humidity Error: {humidity_error}")
        print(f"Soil Moisture (constant): {soil_moisture}")

        # This is your final input vector for prediction
        input_vector = [temp_error, humidity_error, soil_moisture]
        print(f"Input to Prediction Model: {input_vector}")

    except RuntimeError as error:
        print("Reading error:", error.args[0])

    time.sleep(5)
