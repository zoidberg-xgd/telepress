import unittest
from telepress.exceptions import (
    TelePressError,
    DependencyError,
    AuthenticationError,
    ConversionError,
    UploadError,
    SecurityError,
    ValidationError
)


class TestExceptionHierarchy(unittest.TestCase):
    def test_dependency_error_inherits_from_telepress_error(self):
        """Test DependencyError is a TelePressError."""
        error = DependencyError("Missing library")
        self.assertIsInstance(error, TelePressError)
        self.assertIsInstance(error, Exception)

    def test_authentication_error_inherits_from_telepress_error(self):
        """Test AuthenticationError is a TelePressError."""
        error = AuthenticationError("Auth failed")
        self.assertIsInstance(error, TelePressError)

    def test_conversion_error_inherits_from_telepress_error(self):
        """Test ConversionError is a TelePressError."""
        error = ConversionError("Conversion failed")
        self.assertIsInstance(error, TelePressError)

    def test_upload_error_inherits_from_telepress_error(self):
        """Test UploadError is a TelePressError."""
        error = UploadError("Upload failed")
        self.assertIsInstance(error, TelePressError)

    def test_security_error_inherits_from_telepress_error(self):
        """Test SecurityError is a TelePressError."""
        error = SecurityError("Security violation")
        self.assertIsInstance(error, TelePressError)

    def test_validation_error_inherits_from_telepress_error(self):
        """Test ValidationError is a TelePressError."""
        error = ValidationError("Invalid data")
        self.assertIsInstance(error, TelePressError)


class TestExceptionMessages(unittest.TestCase):
    def test_telepress_error_message(self):
        """Test TelePressError preserves message."""
        error = TelePressError("Base error message")
        self.assertEqual(str(error), "Base error message")

    def test_dependency_error_message(self):
        """Test DependencyError preserves message."""
        error = DependencyError("telegraph library is required")
        self.assertEqual(str(error), "telegraph library is required")

    def test_authentication_error_message(self):
        """Test AuthenticationError preserves message."""
        error = AuthenticationError("Invalid token")
        self.assertEqual(str(error), "Invalid token")

    def test_conversion_error_message(self):
        """Test ConversionError preserves message."""
        error = ConversionError("Failed to convert markdown")
        self.assertEqual(str(error), "Failed to convert markdown")

    def test_upload_error_message(self):
        """Test UploadError preserves message."""
        error = UploadError("Network timeout")
        self.assertEqual(str(error), "Network timeout")

    def test_security_error_message(self):
        """Test SecurityError preserves message."""
        error = SecurityError("Zip Slip attack detected")
        self.assertEqual(str(error), "Zip Slip attack detected")

    def test_validation_error_message(self):
        """Test ValidationError preserves message."""
        error = ValidationError("File too large")
        self.assertEqual(str(error), "File too large")


class TestExceptionRaising(unittest.TestCase):
    def test_raise_and_catch_telepress_error(self):
        """Test raising and catching TelePressError."""
        with self.assertRaises(TelePressError):
            raise TelePressError("Test")

    def test_catch_subclass_as_base(self):
        """Test catching subclass exceptions as TelePressError."""
        with self.assertRaises(TelePressError):
            raise ValidationError("Test")
        
        with self.assertRaises(TelePressError):
            raise SecurityError("Test")
        
        with self.assertRaises(TelePressError):
            raise UploadError("Test")

    def test_specific_exception_not_caught_by_sibling(self):
        """Test that specific exceptions aren't caught by sibling types."""
        try:
            raise ValidationError("Test")
        except SecurityError:
            self.fail("ValidationError should not be caught by SecurityError")
        except ValidationError:
            pass  # Expected

    def test_exception_with_context(self):
        """Test exception chaining."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise UploadError("Upload failed") from e
        except UploadError as e:
            self.assertIsInstance(e.__cause__, ValueError)


class TestExceptionUseCases(unittest.TestCase):
    def test_dependency_error_use_case(self):
        """Test DependencyError typical use case."""
        def check_dependency():
            lib = None  # Simulating missing import
            if lib is None:
                raise DependencyError("Required library 'xyz' is not installed")
        
        with self.assertRaises(DependencyError) as ctx:
            check_dependency()
        self.assertIn("xyz", str(ctx.exception))

    def test_validation_error_use_case(self):
        """Test ValidationError typical use case."""
        def validate_file_size(size, max_size):
            if size > max_size:
                raise ValidationError(f"File size {size} exceeds limit {max_size}")
        
        with self.assertRaises(ValidationError) as ctx:
            validate_file_size(1000, 500)
        self.assertIn("1000", str(ctx.exception))
        self.assertIn("500", str(ctx.exception))

    def test_security_error_use_case(self):
        """Test SecurityError typical use case."""
        def check_path(path):
            if ".." in path:
                raise SecurityError(f"Path traversal attempt: {path}")
        
        with self.assertRaises(SecurityError) as ctx:
            check_path("../../../etc/passwd")
        self.assertIn("traversal", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
