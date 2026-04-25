"""
dependencies/auth.py — Dependencia compartida de autenticación Google OAuth.

Verifica el access token de Google llamando al endpoint userinfo.
Todos los routers importan get_current_user desde aquí.
"""

import httpx
from fastapi import Header, HTTPException


async def get_current_user(authorization: str = Header()) -> dict:
    """
    Verifica el Google OAuth access token llamando al userinfo de Google.
    El frontend obtiene este token via Google Identity Services (GIS).

    Retorna: {"uid": str, "email": str, "name": str, "google_token": str}

    Usamos userinfo (no tokeninfo) porque tokeninfo no devuelve `name`.
    El campo google_token se reutiliza para llamadas a Google Calendar API.
    """
    token = authorization.removeprefix("Bearer ").strip()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Token de Google inválido o expirado")

        info = resp.json()
        email = info.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="El token no contiene email")

        return {
            "uid": info.get("sub", ""),
            "email": email,
            "name": info.get("name", ""),
            "google_token": token,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Error al verificar el token de Google")
