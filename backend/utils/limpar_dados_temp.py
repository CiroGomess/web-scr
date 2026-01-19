import os
import glob


def limpar_pasta_temp(temp_dir: str = "data/temp") -> dict:
    """
    Remove todos os arquivos da pasta data/temp (ex: .xlsx, .tmp, etc).
    Não remove subpastas (se existirem).
    """
    try:
        if not os.path.exists(temp_dir):
            return {"success": True, "deleted": 0, "message": f"Pasta '{temp_dir}' não existe."}

        if not os.path.isdir(temp_dir):
            return {"success": False, "error": f"'{temp_dir}' não é uma pasta."}

        deleted = 0
        errors = []

        # remove todos os arquivos diretamente dentro da pasta
        for path in glob.glob(os.path.join(temp_dir, "*")):
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    deleted += 1
            except Exception as e:
                errors.append({"file": path, "error": str(e)})

        if errors:
            return {"success": False, "deleted": deleted, "errors": errors}

        return {"success": True, "deleted": deleted}

    except Exception as e:
        return {"success": False, "error": str(e)}