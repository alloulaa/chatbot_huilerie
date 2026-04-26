from app.repositories.base import BaseRepository


class MachineRepository(BaseRepository):
    def top_failed_machine(self, start_date: str, end_date: str, huilerie: str | None = None):
        params = []
        query = """
            SELECT machine AS machine_code, probleme, huilerie
            FROM vue_machines_probleme
            WHERE 1=1
        """
        if huilerie:
            query += " AND LOWER(huilerie) = LOWER(%s)"
            params.append(huilerie)
        query += " LIMIT 1"
        return self._fetchone(query, tuple(params))

    def machine_state(self, code: str):
        return self._fetchone(
            "SELECT machine AS code, probleme AS etat, huilerie FROM vue_machines_probleme WHERE UPPER(machine)=UPPER(%s) LIMIT 1",
            (code,),
        )
