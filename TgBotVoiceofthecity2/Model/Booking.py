import uuid
from datetime import timedelta
from pydantic import BaseModel, ConfigDict
from pydantic_extra_types.pendulum_dt import Date
from datetime import time

from Model.Location import LocationZone


class Booking(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: uuid.UUID
    date: Date
    time: time
    duration: timedelta
    location: LocationZone
