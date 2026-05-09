"""Configuration validation script to ensure .env is properly loaded."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def validate_config():
    """Validate that all required configurations are loaded from .env file."""
    
    print("=" * 70)
    print("Configuration Validation")
    print("=" * 70)
    print()
    
    try:
        from analysis_agent_system.app.config import settings
        
        issues = []
        warnings = []
        
        # Check critical database configuration
        print("📊 Database Configuration:")
        if not settings.DB_HOST or settings.DB_HOST == "localhost":
            warnings.append("DB_HOST is using default value 'localhost'")
        print(f"  ✓ DB_HOST: {settings.DB_HOST}")
        
        if not settings.DB_NAME:
            issues.append("DB_NAME is not configured")
        else:
            print(f"  ✓ DB_NAME: {settings.DB_NAME}")
        
        if not settings.DB_USER:
            issues.append("DB_USER is not configured")
        else:
            print(f"  ✓ DB_USER: {settings.DB_USER}")
        
        if not settings.DB_PASSWORD:
            warnings.append("DB_PASSWORD is empty (may be intentional for local development)")
        else:
            print(f"  ✓ DB_PASSWORD: {'*' * len(settings.DB_PASSWORD)}")
        
        print(f"  ✓ DB_PORT: {settings.DB_PORT}")
        print()
        
        # Check LLM configuration
        print("🤖 LLM Configuration:")
        if not settings.VLLM_API_BASE or settings.VLLM_API_BASE == "http://localhost:8080/v1":
            warnings.append("VLLM_API_BASE is using default value")
        print(f"  ✓ VLLM_API_BASE: {settings.VLLM_API_BASE}")
        
        if not settings.MODEL_NAME or settings.MODEL_NAME == "qwen3-vl-8b-instruct":
            warnings.append("MODEL_NAME is using default value")
        print(f"  ✓ MODEL_NAME: {settings.MODEL_NAME}")
        
        print(f"  ✓ VLLM_API_KEY: {'Set' if settings.VLLM_API_KEY else 'Empty'}")
        print()
        
        # Check application settings
        print("⚙️ Application Settings:")
        print(f"  ✓ APP_HOST: {settings.HOST}")
        print(f"  ✓ APP_PORT: {settings.PORT}")
        print(f"  ✓ DEBUG: {settings.DEBUG}")
        print()
        
        # Check security settings
        print("🔒 Security Settings:")
        if settings.AUTH_SECRET_KEY == "change-me-in-production":
            warnings.append("AUTH_SECRET_KEY is using default value - CHANGE THIS IN PRODUCTION!")
        else:
            print(f"  ✓ AUTH_SECRET_KEY: Set (length: {len(settings.AUTH_SECRET_KEY)})")
        print()
        
        # Test database URL generation
        print("🔗 Database URL Test:")
        try:
            db_url = settings.DATABASE_URL
            # Mask password for security
            if '@' in db_url:
                parts = db_url.split('@')
                creds = parts[0].split('://')[1]
                masked_url = f"{parts[0].split('://')[0]}://***:***@{parts[1]}"
                print(f"  ✓ Generated: {masked_url}")
            else:
                print(f"  ⚠ Generated: {db_url}")
        except Exception as e:
            issues.append(f"Failed to generate DATABASE_URL: {e}")
        print()
        
        # Summary
        print("=" * 70)
        if issues:
            print("❌ CRITICAL ISSUES FOUND:")
            for issue in issues:
                print(f"   • {issue}")
            print()
        
        if warnings:
            print("⚠️  WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
            print()
        
        if not issues and not warnings:
            print("✅ All configurations loaded successfully!")
            print()
            print("Note: Some values may be using fallback defaults.")
            print("To use custom values, edit the .env file.")
        elif not issues:
            print("✅ Configuration is functional but has warnings.")
            print("   Review warnings above and update .env if needed.")
        else:
            print("❌ Configuration has critical issues.")
            print("   Please fix the issues before starting the application.")
            sys.exit(1)
        
        print("=" * 70)
        
    except ImportError as e:
        print(f"❌ Failed to import configuration module: {e}")
        print("   Make sure python-dotenv is installed: pip install python-dotenv")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    validate_config()
