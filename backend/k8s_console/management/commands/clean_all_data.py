"""Django management command: clean ALL data from MySQL.
Drop every table managed by this project, then recreate via SQL file.

Usage:
    # Dry-run: 仅打印将执行的SQL，不实际操作
    python manage.py clean_all_data --dry-run --settings=k8s_console.settings_dev

    # 执行清理 + 重建
    python manage.py clean_all_data --settings=k8s_console.settings_dev

    # 指定 SQL 文件路径
    python manage.py clean_all_data --sql-file sql/init_database.sql --settings=k8s_console.settings_dev
"""
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "清理所有数据并重建表（DROP + 执行 SQL init 文件）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅打印将要执行的 DROP 语句，不实际执行",
        )
        parser.add_argument(
            "--sql-file",
            type=str,
            default="sql/init_database.sql",
            help="初始化 SQL 文件路径（相对于项目根目录）",
        )

    def handle(self, *args, **options):
        sql_file = options["sql_file"]
        dry_run = options["dry_run"]

        # Resolve SQL file path
        base_dir = Path(settings.BASE_DIR)
        sql_path = base_dir / sql_file

        if not sql_path.exists():
            self.stderr.write(self.style.ERROR(f"SQL 文件不存在: {sql_path}"))
            sys.exit(1)

        # Tables managed by this project (matching the SQL init file)
        # Order matters: child tables first to avoid FK constraint errors
        project_tables = [
            "password_reset_token",
            "audit_log",
            "cluster",
            "user",
            "django_migrations",
        ]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN 模式 — 将执行以下操作 ==="))
            self.stdout.write("")
            for table in project_tables:
                self.stdout.write(f"  DROP TABLE IF EXISTS `{table}`;")
            self.stdout.write("")
            self.stdout.write(f"  然后执行: source {sql_path};")
            self.stdout.write(self.style.WARNING("=== DRY RUN 结束，未做任何更改 ==="))
            return

        # Confirm
        self.stdout.write(self.style.ERROR("=" * 60))
        self.stdout.write(self.style.ERROR("⚠️  即将删除所有数据并重建表！这是不可逆操作！"))
        self.stdout.write(self.style.ERROR(f"数据库: {settings.DATABASES['default']['NAME']}"))
        self.stdout.write(self.style.ERROR(f"表将被删除: {', '.join(project_tables)}"))
        self.stdout.write(self.style.ERROR("=" * 60))

        confirmed = input("请输入 'yes' 确认: ")
        if confirmed != "yes":
            self.stdout.write(self.style.WARNING("已取消。"))
            return

        # Step 1: Drop all project tables
        from django.db import connection
        with connection.cursor() as cursor:
            # Disable FK checks while dropping
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in project_tables:
                self.stdout.write(f"  DROP TABLE IF EXISTS `{table}` ...")
                cursor.execute(f"DROP TABLE IF EXISTS `{table}`;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        self.stdout.write(self.style.SUCCESS("  所有表已删除。"))

        # Step 2: Execute SQL init file
        sql_content = sql_path.read_text(encoding="utf-8")
        # Remove comments and split by semicolons to execute statement by statement
        statements = []
        current = []
        for line in sql_content.split("\n"):
            stripped = line.strip()
            # Skip pure comment lines and empty lines
            if not stripped or stripped.startswith("--"):
                continue
            current.append(line)
            if stripped.endswith(";"):
                stmt = "\n".join(current).rstrip(";")
                if stmt.strip():
                    statements.append(stmt)
                current = []

        from django.db import connection
        with connection.cursor() as cursor:
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    # Ignore errors like "database exists" or "table exists" (we used IF NOT EXISTS)
                    self.stdout.write(self.style.WARNING(f"  跳过（可能已存在）: {str(e)[:80]}"))

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ 数据库已重建完成！"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write("下一步:")
        self.stdout.write("  1. python manage.py init_admin --settings=k8s_console.settings_dev")
        self.stdout.write("  2. python manage.py migrate --fake --settings=k8s_console.settings_dev")
