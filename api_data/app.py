from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import json
import os

app = FastAPI()

class FlightSearchModel(BaseModel):
    ciudad_origen: str
    ciudad_destino: str
    fecha_salida: str
    fecha_vuelta: str
    stops: int = 0
    adults: int = 1
    children: int = 0
    cabin_class: str = "ECONOMY"
    currency: str = "EUR"

@app.get("/")
def read_root():
    return {"message": "Welcome to the API Data application!"}

@app.post("/search_flights")
async def search_flights(body: FlightSearchModel):

    print(body)
    
    return [
        {
            "departureAirport": {
                "type": "AIRPORT",
                "code": "ALC",
                "name": "Alicante-Elche Miguel Hernández Airport",
                "city": "ALC",
                "cityName": "Alicante",
                "country": "ES",
                "countryName": "Spain",
                "province": "Valencia Community"
            },
            "arrivalAirport": {
                "type": "AIRPORT",
                "code": "DEL",
                "name": "Delhi International Airport",
                "city": "DEL",
                "cityName": "New Delhi",
                "country": "IN",
                "countryName": "India"
            },
            "departureTime": "2025-04-24T23:35:00",
            "arrivalTime": "2025-04-26T05:20:00"
        }
    ]