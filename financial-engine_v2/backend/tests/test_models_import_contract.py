def test_backend_models_exports_company_model():
    import app.models
    from app.models.companies import Company

    assert app.models.Company is Company
    assert Company.__tablename__ == "companies"


def test_backend_main_imports_with_models_package():
    import app.main  # noqa: F401


def test_company_model_matches_companies_migration_contract():
    from app.models.companies import Company

    table = Company.__table__

    assert [column.name for column in table.primary_key.columns] == [
        "ticker",
        "exchange",
    ]
    assert set(table.columns.keys()) == {
        "ticker",
        "exchange",
        "company_name",
        "isin",
        "figi",
        "listing_date",
        "delisting_date",
        "status",
        "sector",
        "industry",
        "website",
        "updated_at",
    }
    assert {constraint.name for constraint in table.constraints} >= {
        "uq_companies_isin",
        "uq_companies_figi",
    }
    assert {index.name for index in table.indexes} == {
        "ix_companies_exchange_status",
    }
