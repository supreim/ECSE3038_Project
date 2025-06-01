**SMART HUB FastAPI OVERVIEW**

1. PUT Request (/settings)This endpoint allows the frontend software (like the website) to send user preferences to the server. The request includes a JSON body with temperature, light activation time, and light duration. If "sunset" is chosen, the server fetches the sunset time from an external API based on a specific location; otherwise, it uses the user-supplied time. The duration is then parsed, and the calculated light-off time is determined. These details are stored and logged to the terminal. The response includes the user's settings and calculated times.

2. POST Request (/sensor)Used by the ESP32 hardware to send sensor readings (temperature and presence) to the server. The server retrieves the most recent user settings and evaluates whether the conditions are met to activate the fan or light. The fan is turned on if the temperature exceeds the set threshold and someone is present. Similarly, the light turns on if the current time matches the user-set or sunset time and someone is present, remaining on for the specified duration. The API returns the states of both devices (fan and light).

3. GET Request (/graph?size=n)This endpoint is used by the client interface to fetch recent sensor data logs, which are used to generate graphs on the webpage. It accepts a query parameter n (between 1 and 500) to limit the number of records returned. The response is a JSON list containing dictionaries of temperature, presence, and timestamps.

**ESP32 HARDWARE CLIENT OVERVIEW**
The ESP32 is responsible for gathering data from the attached sensors, such as temperature and motion (presence). It sends this data to the API and waits for instructions. Based on the response from the server, which decides whether to activate the fan or light, the ESP32 updates the status of these devices accordingly. All decision-making is offloaded to the server to keep the microcontroller lightweight and responsive.

