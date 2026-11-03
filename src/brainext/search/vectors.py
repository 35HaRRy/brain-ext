"""Two cosine backends over the same standard float32 BLOB storage."""

import math
import sqlite3
import struct


def pack(vector, dimension=None) -> bytes:
    values = [float(v) for v in vector]
    if not values or (dimension is not None and len(values) != dimension):
        raise ValueError("Embedding boyutu uyuşmuyor")
    if not all(math.isfinite(v) for v in values) or not any(values):
        raise ValueError("Embedding sonlu ve sıfırdan farklı olmalı")
    try:
        return struct.pack("<" + "f" * len(values), *values)
    except OverflowError:
        raise ValueError("Embedding float32 aralığı dışında") from None


class VectorBackend:
    def __init__(self, db, *, prefer="sqlite-vec"):
        self.db = db
        self.name = "numpy"
        if prefer == "sqlite-vec":
            try:
                import sqlite_vec

                try:
                    db.enable_load_extension(True)
                    sqlite_vec.load(db)
                finally:
                    db.enable_load_extension(False)
                self.name = "sqlite-vec"
            except (ImportError, AttributeError, OSError, sqlite3.Error):
                pass
        if self.name == "numpy":
            import numpy as np

            self.np = np

    def rank(self, rows, query):
        blob = pack(query)
        result = []
        for id, vector in rows:
            if len(vector) != len(blob):
                raise ValueError("Kayıtlı vektör boyutu uyuşmuyor; --reembed gerekli")
            if self.name == "sqlite-vec":
                distance = self.db.execute("select vec_distance_cosine(?,?)", (vector, blob))
                score = 1.0 - distance.fetchone()[0]
            else:
                a = self.np.frombuffer(vector, dtype="<f4")
                b = self.np.frombuffer(blob, dtype="<f4")
                score = float(self.np.dot(a, b) / (self.np.linalg.norm(a) * self.np.linalg.norm(b)))
            result.append((id, score))
        return sorted(result, key=lambda item: (-item[1], item[0]))
