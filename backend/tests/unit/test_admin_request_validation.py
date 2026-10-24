import pytest
from pydantic import ValidationError

from src.api.admin import CreateCategoryRequest, RenameCategoryRequest, UpdateUserRequest


class TestUpdateUserRequest:
    def test_all_fields_optional(self):
        body = UpdateUserRequest()
        assert body.role is None and body.new_password is None

    def test_valid_values_pass(self):
        body = UpdateUserRequest(role="editor", is_active=False, new_password="x" * 8)
        assert body.role == "editor"

    @pytest.mark.parametrize("role", ["superuser", "", "Admin"])
    def test_invalid_role_rejected(self, role):
        with pytest.raises(ValidationError):
            UpdateUserRequest(role=role)

    @pytest.mark.parametrize("pw", ["short", "x" * 129])
    def test_invalid_password_length_rejected(self, pw):
        with pytest.raises(ValidationError):
            UpdateUserRequest(new_password=pw)


class TestCategoryRequests:
    @pytest.mark.parametrize("model", [CreateCategoryRequest, RenameCategoryRequest])
    def test_name_is_stripped(self, model):
        assert model(name="  核心系統 ").name == "核心系統"

    @pytest.mark.parametrize("model", [CreateCategoryRequest, RenameCategoryRequest])
    @pytest.mark.parametrize("name", ["", "   ", "x" * 101])
    def test_invalid_name_rejected(self, model, name):
        with pytest.raises(ValidationError):
            model(name=name)
