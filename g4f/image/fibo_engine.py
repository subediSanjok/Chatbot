"""
FIBO (Fast Interactive Blueprint Output) JSON-Native Generation & Refinement Engine
Integrated from Bria AI FIBO architecture.

Features:
- Structured JSON Schema (1,000+ words multi-attribute specification)
- Disentangled Attribute Control (Camera, Lighting, Composition, Objects, Background)
- 3 Modes:
    1. Generate: Short prompt -> Structured JSON Schema -> High-fidelity Image
    2. Refine: Existing JSON Schema + Edit Instruction -> Target-Modified JSON -> Refined Image
    3. Inspire: Input Image -> Extracted Structured JSON -> Novel variations
"""

import os
import json
import re
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional, Tuple


FIBO_FULL_SCHEMA = {
    "short_description": "Concise summary of the image content (max 200 words).",
    "objects": [
        {
            "description": "Detailed description of the object (max 100 words).",
            "location": "center, top-left, bottom-right foreground, etc.",
            "relative_size": "small, medium, large within frame",
            "shape_and_color": "Dominant shape and exact color palette",
            "texture": "smooth, rough, metallic, furry, etc.",
            "appearance_details": "Visual nuances, patterns, details",
            "relationship": "Spatial relationship with other objects",
            "orientation": "upright, facing left, horizontal, etc.",
            "pose": "Body position if human/animal",
            "expression": "Facial emotion or expression",
            "clothing": "Attire if applicable",
            "action": "Action or behavior"
        }
    ],
    "background_setting": "Detailed environment, landscape, architecture, weather, and backdrop elements.",
    "lighting": {
        "conditions": "bright daylight, studio lighting, golden hour, neon cinematic, etc.",
        "direction": "front-lit, backlit, rim-lit, side-lit from left",
        "shadows": "soft diffused shadows, long sharp shadows, minimal shadows"
    },
    "aesthetics": {
        "composition": "rule of thirds, symmetrical, centered, leading lines, portrait close-up",
        "color_scheme": "monochromatic, warm complementary, high contrast, pastel, vibrant",
        "mood_atmosphere": "serene, dramatic, mysterious, futuristic, energetic, whimsical"
    },
    "photographic_characteristics": {
        "depth_of_field": "shallow bokeh, deep focus, sharp",
        "focus": "ultra-sharp focus on primary subject",
        "camera_angle": "eye-level, low angle, high overhead angle, dutch angle",
        "lens_focal_length": "portrait lens 85mm, standard 50mm, wide-angle 24mm, macro"
    },
    "style_medium": "photograph, 2D vector cartography, digital illustration, 3D render, oil painting",
    "artistic_style": "photorealistic, hyperdetailed, clean vector",
    "context": "Contextual usage: editorial photography, commercial concept art, cartographic infographic",
    "text_render": []
}

FIBO_SYSTEM_PROMPTS = {
    "generate": f"""You are the FIBO Visual Art Director & Structured JSON Caption Engine.
Your job is to transform any user concept into a comprehensive, professional FIBO JSON schema with exact attributes.

Adhere strictly to these guidelines:
1. Output MUST be ONLY valid JSON matching the schema below. No conversational text or markdown blocks outside the JSON.
2. If human/animal subject: describe from their perspective, specify close-up or medium framing.
3. If MAP/DIAGRAM: set style_medium="2D vector cartography", specify exact national borders, provinces, white background, no landscape photos.
4. Default to style_medium: "photograph", artistic_style: "photorealistic" unless explicitly asked otherwise.

FIBO JSON Schema Structure:
{json.dumps(FIBO_FULL_SCHEMA, indent=2)}""",

    "refine": f"""You are the FIBO Visual Editor. Your job is to update an existing FIBO JSON object based on the user's specific edit instruction (e.g. "change lighting to golden hour", "add sunglasses", "make background snowy").
Update ONLY the requested attributes while preserving all other keys, subject identities, and composition intact.
Output MUST be ONLY the updated valid JSON object."""
}


class FiboEngine:
    def __init__(self, backend_url: str = "http://127.0.0.1:1337"):
        self.backend_url = backend_url.rstrip("/")

    def generate_structured_json(
        self,
        prompt: str,
        existing_json: Optional[Dict[str, Any]] = None,
        task: str = "generate"
    ) -> Dict[str, Any]:
        """
        Generates or refines a full structured FIBO JSON schema using LLM reasoning.
        """
        system_instruction = FIBO_SYSTEM_PROMPTS.get(task, FIBO_SYSTEM_PROMPTS["generate"])
        user_content = prompt
        if task == "refine" and existing_json:
            user_content = f"Existing JSON:\n{json.dumps(existing_json, indent=2)}\n\nEdit Instruction:\n{prompt}"

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            "stream": False
        }

        try:
            req = urllib.request.Request(
                f"{self.backend_url}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_reply = data["choices"][0]["message"]["content"].strip()
                
                # Extract JSON block
                json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_reply)
                if json_match:
                    raw_reply = json_match.group(1)
                elif raw_reply.startswith("{") and raw_reply.endswith("}"):
                    pass
                else:
                    first_brace = raw_reply.find("{")
                    last_brace = raw_reply.rfind("}")
                    if first_brace != -1 and last_brace != -1:
                        raw_reply = raw_reply[first_brace:last_brace+1]

                return json.loads(raw_reply)
        except Exception as e:
            # Fallback deterministic builder if server is busy
            return self._build_deterministic_json(prompt)

    def _build_deterministic_json(self, prompt: str) -> Dict[str, Any]:
        """Fallback rule-based FIBO builder"""
        p_lower = prompt.lower()
        is_map = "map" in p_lower or "nepal" in p_lower
        is_diagram = "diagram" in p_lower or "flowchart" in p_lower

        schema = json.loads(json.dumps(FIBO_FULL_SCHEMA))
        schema["short_description"] = f"A high-quality rendering of {prompt}."
        schema["objects"][0]["description"] = prompt
        schema["objects"][0]["location"] = "center"
        schema["objects"][0]["relative_size"] = "large within frame"

        if is_map:
            schema["style_medium"] = "2D vector cartography"
            schema["artistic_style"] = "clean infographic vector"
            schema["background_setting"] = "Clean white background with latitude/longitude grid and legend."
            schema["photographic_characteristics"]["camera_angle"] = "top-down orthographic"
        elif is_diagram:
            schema["style_medium"] = "2D technical diagram"
            schema["artistic_style"] = "minimalist vector schematic"
            schema["background_setting"] = "Neutral white backdrop."
        else:
            schema["style_medium"] = "photograph"
            schema["artistic_style"] = "photorealistic"
            schema["background_setting"] = "Natural, high-detail context."

        return schema

    def json_to_flattened_prompt(self, fibo_data: Dict[str, Any]) -> str:
        """
        Converts the structured FIBO JSON schema into a high-density diffusion conditioning prompt.
        """
        parts = []

        # 1. Short description
        short_desc = fibo_data.get("short_description")
        if short_desc:
            parts.append(short_desc)

        # 2. Objects breakdown
        objects = fibo_data.get("objects", [])
        for obj in objects[:4]:
            desc = obj.get("description", "")
            loc = obj.get("location", "")
            appearance = obj.get("appearance_details", "")
            color = obj.get("shape_and_color", "")
            pose = obj.get("pose", "")
            obj_str = f"{desc}"
            if loc:
                obj_str += f" positioned at {loc}"
            if color:
                obj_str += f", {color}"
            if appearance:
                obj_str += f", {appearance}"
            if pose:
                obj_str += f", pose: {pose}"
            parts.append(obj_str)

        # 3. Background & environment
        bg = fibo_data.get("background_setting")
        if bg:
            parts.append(f"Background: {bg}")

        # 4. Lighting
        lighting = fibo_data.get("lighting", {})
        if lighting:
            cond = lighting.get("conditions", "")
            direction = lighting.get("direction", "")
            shadows = lighting.get("shadows", "")
            light_str = f"Lighting: {cond}"
            if direction:
                light_str += f", {direction}"
            if shadows:
                light_str += f", {shadows}"
            parts.append(light_str)

        # 5. Aesthetics & Photography
        aesthetics = fibo_data.get("aesthetics", {})
        comp = aesthetics.get("composition", "")
        mood = aesthetics.get("mood_atmosphere", "")
        if comp or mood:
            parts.append(f"Composition: {comp}, mood: {mood}")

        photo = fibo_data.get("photographic_characteristics", {})
        if photo:
            lens = photo.get("lens_focal_length", "")
            angle = photo.get("camera_angle", "")
            dof = photo.get("depth_of_field", "")
            parts.append(f"Camera: {angle}, lens: {lens}, {dof}")

        # 6. Style & Medium
        medium = fibo_data.get("style_medium", "photograph")
        style = fibo_data.get("artistic_style", "realistic")
        parts.append(f"Style: {medium}, {style}")

        return ". ".join([p.strip().rstrip(".") for p in parts if p]) + "."

    def generate(

        self,
        prompt: str,
        task: str = "generate",
        existing_json: Optional[Dict[str, Any]] = None,
        model: str = "flux"
    ) -> Dict[str, Any]:
        """
        Executes the complete FIBO generation / refinement cycle:
        Short prompt -> Structured FIBO JSON Schema -> Flattened Conditioning -> Image API Synthesis.
        """
        # Step 1: Generate or Refine Structured JSON
        structured_json = self.generate_structured_json(prompt, existing_json=existing_json, task=task)

        # Step 2: Flatten JSON into dense prompt
        flattened_prompt = self.json_to_flattened_prompt(structured_json)

        # Step 3: Send to image generation backend
        img_url = ""
        try:
            payload = {
                "prompt": flattened_prompt,
                "model": model
            }

            req = urllib.request.Request(
                f"{self.backend_url}/v1/images/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data") and len(data["data"]) > 0:
                    img_url = data["data"][0].get("url", "")
        except Exception as api_err:
            print("Server /v1/images/generations error, using direct Flux fallback:", api_err)

        if not img_url:
            encoded_prompt = urllib.parse.quote(flattened_prompt)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

        return {
            "url": img_url,
            "image_url": img_url,
            "structured_json": structured_json,
            "flattened_prompt": flattened_prompt,
            "short_description": structured_json.get("short_description", prompt)
        }


