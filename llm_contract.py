from typing import Any, Dict


def validate_contract(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Contract payload must be a JSON object")

    if "reply_text" not in data or not isinstance(data["reply_text"], str):
        raise ValueError("Contract must include reply_text")

    image = data.get("image")
    if not isinstance(image, dict):
        raise ValueError("Contract must include image object")

    do_generate = image.get("do_generate")
    if not isinstance(do_generate, bool):
        raise ValueError("image.do_generate must be boolean")

    scene_append = image.get("scene_append")
    if do_generate and (not isinstance(scene_append, str) or not scene_append.strip()):
        raise ValueError("scene_append required when do_generate is true")

    negative_append = image.get("negative_append")
    if negative_append is None:
        image["negative_append"] = ""
    elif not isinstance(negative_append, str):
        raise ValueError("negative_append must be string or null")

    return data
