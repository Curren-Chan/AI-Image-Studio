import logging

from services.base import BaseService


class LibraryService(BaseService):
    def get_characters(self) -> list:
        try:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT id, name, description, image_path, prompt_fragment, tags "
                    "FROM characters ORDER BY name ASC;"
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as exc:
            logging.error("Failed to fetch characters: %s", exc)
            return []

    def create_character(
        self,
        name: str,
        description: str,
        image_path: str,
        prompt_fragment: str,
        tags: str = "",
    ) -> int:
        try:
            with self.connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO characters
                        (name, description, image_path, prompt_fragment, tags)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (name, description, image_path, prompt_fragment, tags),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception as exc:
            logging.error("Failed to create character: %s", exc)
            return -1

    def delete_character(self, character_id: int) -> bool:
        try:
            with self.connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM characters WHERE id = ?;", (character_id,)
                )
                conn.commit()
                return cursor.rowcount == 1
        except Exception as exc:
            logging.error("Failed to delete character: %s", exc)
            return False

    def get_products(self) -> list:
        try:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT id, name, description, brand, image_path, prompt_fragment, tags "
                    "FROM products ORDER BY name ASC;"
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as exc:
            logging.error("Failed to fetch products: %s", exc)
            return []

    def create_product(
        self,
        name: str,
        description: str,
        brand: str,
        image_path: str,
        prompt_fragment: str,
        tags: str = "",
    ) -> int:
        try:
            with self.connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO products
                        (name, description, brand, image_path, prompt_fragment, tags)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (name, description, brand, image_path, prompt_fragment, tags),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception as exc:
            logging.error("Failed to create product: %s", exc)
            return -1

    def delete_product(self, product_id: int) -> bool:
        try:
            with self.connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM products WHERE id = ?;", (product_id,)
                )
                conn.commit()
                return cursor.rowcount == 1
        except Exception as exc:
            logging.error("Failed to delete product: %s", exc)
            return False
