"""User-installable declarative Skill APIs."""
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from skills.store import (
    SkillInstallPipeline,
    list_user_skills,
    set_enabled,
    template,
    uninstall,
)
from skills import loader as skills_loader


router = APIRouter()


@router.get("/user-skills")
def list_all(owner_id: str = Query("local-user")):
    return {
        "builtin": [skill for skill in skills_loader.catalog() if skill.get("source") == "builtin"],
        "installed": list_user_skills(owner_id),
    }


@router.get("/user-skills/template")
def get_template():
    return {"filename": "my-custom-skill.yaml", "content": template()}


@router.post("/user-skills/install")
async def install(
    file: UploadFile = File(...),
    owner_id: str = Query("local-user"),
):
    try:
        result = SkillInstallPipeline().install(await file.read(), file.filename or "skill.yaml", owner_id)
        return {"ok": True, **result}
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "pipeline": getattr(exc, "pipeline", [])},
        ) from exc


@router.patch("/user-skills/{name}")
def update(name: str, body: dict, owner_id: str = Query("local-user")):
    try:
        return {"ok": True, "skill": set_enabled(name, bool(body.get("enabled")), owner_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/user-skills/{name}")
def remove(name: str, owner_id: str = Query("local-user")):
    try:
        uninstall(name, owner_id)
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
