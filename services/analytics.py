import time
import json
import os
from services.geometry import get_store_zones

class AnalyticsService:
    def __init__(self):
        # Load zones from the config file we just created
        self.zones = get_store_zones()
        self.current_occupancy = {z.name: 0 for z in self.zones}
        
    def update(self, tracks):
        """
        Maps (x,y) coordinates to Semantic Zones.
        """
        self.current_occupancy = {z.name: 0 for z in self.zones}
        
        for track in tracks:
            cx = int(track['x'] + track['width'] / 2)
            cy = int(track['y'] + track['height'] / 2)
            
            track['current_zone'] = None
            
            for zone in self.zones:
                if zone.contains((cx, cy)):
                    self.current_occupancy[zone.name] += 1
                    track['current_zone'] = zone.name 
                    break
    
    def get_llm_context(self):
        """Generates the text payload for Bedrock"""
        summary = "Current Store Status:\n"
        active_zones = [f"- {z}: {c} people" for z, c in self.current_occupancy.items() if c > 0]
        
        if not active_zones:
            return summary + "Store is currently empty."
        
        return summary + "\n".join(active_zones)