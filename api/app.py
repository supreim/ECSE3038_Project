from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError
from fastapi.responses import JSONResponse
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID, uuid4
import re
from datetime import timedelta, datetime
import httpx
import tzlocal

timezone = tzlocal.get_localzone()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (replace "*" with your ESP32 IP for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (PUT, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

hub_data = []
sensor_data = []

class Settings(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_temp: int 
    user_light: str 
    light_duration: str

class Graph(BaseModel):
    temperature: float 
    presence: int 
    date_time: datetime = Field(default_factory=lambda: datetime.now(timezone))

class GraphResponse(BaseModel):
    temperature: float
    presence: int 
    datetime: str 

# Sirs parse time function
############
regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')
def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)
############

@app.put("/settings")
async def user_settings(settings_req:Settings):
    print("Received settings from user: ")
    for key, value in settings_req.dict().items():
        print(f"  {key}: {value}")

    hub_data.clear()
    hub_data.append(settings_req)

       #light start time 
    if settings_req.user_light == "sunset":
        light_start_time = await get_sunset_time(lat=18.16,lng=-77.03)
    else:
        try:
            light_start_time = datetime.strptime(settings_req.user_light, "%H:%M:%S").time()
        except ValueError:
            raise HTTPException(status_code= 400, detail="Invalid user_light time")
        

    on_duration = parse_time(settings_req.light_duration)
    if on_duration is None:
        raise HTTPException(status_code= 400, detail = "Invalid light duration. Example Format:'1h30m' ")

    start_datetime = datetime.combine(datetime.now(timezone).date(), light_start_time)

    light_stop_time = (start_datetime + on_duration).time()

    print(f"Light turn on time: {light_start_time.strftime('%H:%M:%S')}")
    print(f"Light turn off time: {light_stop_time.strftime('%H:%M:%S')}")

    return {
        "_id": str(settings_req.id),
        "user_temp": settings_req.user_temp,
        "user_light": light_start_time.strftime("%H:%M:%S"),
        "light_time_off": light_stop_time.strftime("%H:%M:%S")
    }

@app.post("/sensors_data")
async def process_sensor_data(output_request:Graph):
    print ("Post request received: ")
    ##print (output_request.dict())
    
    if not hub_data:
        raise HTTPException(status_code=400, detail = "Settings not found")
    settings = hub_data[-1]
    sensor_data.append(output_request)

    fan_status = "off"
    if output_request.temperature >= settings.user_temp and output_request.presence !=0 :
        fan_status = "on"

    light_status = "off"
    try: 
        present_time = datetime.now(timezone).time()
        light_turn_on = datetime.strptime(settings.user_light, "%H:%M:%S").time()
        on_duration = parse_time(settings.light_duration)
        light_turn_off = (datetime.combine(datetime.now(timezone).date(),light_turn_on)+ on_duration).time()

        if (light_turn_on <= present_time <= light_turn_off) and output_request.presence != 0:
            light_status = "on"
    except:
        pass


    JSONformat_data = {
        "temperature": output_request.temperature,
        "presence": output_request.presence,
        "date_time": output_request.date_time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    print(JSONResponse(content=[JSONformat_data]).body.decode())
    return {"fan":fan_status, "light": light_status}


async def get_sunset_time(lat: float, lng: float):
    url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            json_data = response.json()
            sunset_utc_str = json_data["results"]["sunset"]
            sunset_utc = datetime.fromisoformat(sunset_utc_str.replace("Z", "+00:00"))
            
            sunset_local = sunset_utc.astimezone(timezone)
            return sunset_local.time()
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch sunset time")

@app.get("/graph", response_model=List[GraphResponse])
async def get_graph_data(size: int = Query(..., gt=0, le = 500)):
    
    if not sensor_data:
        raise HTTPException(status_code=404,detail= "No data available")
    
    try: 

        data_returned = sensor_data[:min(size,len (sensor_data))]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    collected_data = [
        {
            "temperature": item.temperature,
            "presence": item.presence,
            "datetime": item.date_time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        for item in data_returned
    ]

    return JSONResponse(content=collected_data)



