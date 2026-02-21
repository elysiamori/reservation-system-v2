import unittest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class TestDatabaseConnection(unittest.TestCase):
    def setUp(self):
        self.database_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/reservation_system"

        self.engine = create_engine(self.database_url)

    def test_database_connection_success(self):
        """Test that the application can successfully connect to Supabase."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                value = result.scalar()
                self.assertEqual(value, 1)
                print("\n✅ Connection to Supabase PostgreSQL successful via Pooler!")

        except SQLAlchemyError as e:
            self.fail(f"❌ Database connection failed: {str(e)}")


if __name__ == '__main__':
    unittest.main()