"""
Analytics Service - Connects Tracking to Zones
"""
import time
from services.geometry import get_store_zones

class AnalyticsService:
    def __init__(self):
        self.zones = get_store_zones()
        # "Memory" of where people are
        self.current_occupancy = {z.name: 0 for z in self.zones}
        
    def update(self, tracks):
        """
        Takes list of track dictionaries: [{'id': 1, 'x': 10, ...}, ...]
        Updates occupancy counts and modifies the tracks with zone info.
        """
        # Reset counts for this frame
        self.current_occupancy = {z.name: 0 for z in self.zones}
        
        for track in tracks:
            # Handle Dictionary access (Fixes the AttributeError)
            # Center Point Calculation: x + width/2, y + height/2
            cx = int(track['x'] + track['width'] / 2)
            cy = int(track['y'] + track['height'] / 2)
            
            # Default to no zone
            track['current_zone'] = None
            
            for zone in self.zones:
                if zone.contains((cx, cy)):
                    self.current_occupancy[zone.name] += 1
                    # Inject zone info directly into the track dict
                    track['current_zone'] = zone.name 
                    break
    
    def get_llm_context(self):
        """Generates the context string for Bedrock"""
        summary = "Current Store Status:\n"
        active_zones = [f"- {z}: {c} people" for z, c in self.current_occupancy.items() if c > 0]
        
        if not active_zones:
            return summary + "Store is currently empty."
        
        return summary + "\n".join(active_zones)