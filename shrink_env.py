import os
import sys
from sys import argv

variables_per_service = {
        "bot" : ["POSTGRES_USER", "POSTGRES_PASSWORD", "SKIP_UPDATES", "DELETE_MESSAGES_AFTER_SEC",
                 "DELETE_MESSAGES_WITHOUT_ORDERS_AFTER_SEC", "DELETE_MESSAGES_WITH_FINISHED_ORDERS_AFTER_SEC",
                 "TOKEN", "TMP_DIR", "JWT_SECRET_KEY", "ADMIN_CHAT_ID", "ERROR_LOGS_CHAT_ID", "STATS_CHAT_ID",
                 "STATS_PERIOD", "SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID","KEYSTORE_PASSWORD",
                 "USER_ID_HASH_SALT", "FAILED_BUILD_COUNT_ALLOWED", "UPDATES_ALLOWED", "SET_BOT_NAME_AND_DESCRIPTION"],
        "build_worker": ["DATA_DIR", "TMP_DIR", "MOCK_BUILD", "WORKER_CONTROLLER_HOST", "WORKER_CHECK_INTERVAL_SEC",
                         "WORKER_JWT", "KEYSTORE_PASSWORD", "BUILD_DOCKER_IMAGE_NAME", "ALLOW_BUILD_SOURCES_ONLY"],
        "clean_orders_queue": ["POSTGRES_USER", "POSTGRES_PASSWORD", "CONSIDER_WORKER_OFFLINE_AFTER_SEC",
                               "DELETE_USER_BUILD_STATS_AFTER_SEC"],
        "workers_controller": ["POSTGRES_USER", "POSTGRES_PASSWORD", "JWT_SECRET_KEY", "TMP_DIR", "USER_ID_HASH_SALT"],
        "migrations": ["POSTGRES_USER", "POSTGRES_PASSWORD"],
        "tests": []
    }

def shrink_env():
    validate_args()
    lines = read_all_env_lines()
    lines = filter_env_lines(lines)
    print(lines)
    save_env(lines)
    remove_unused_files()


def validate_args():
    if len(argv) != 2:
        exit_with_error(f"Usage: python {os.path.basename(__file__)} SERVICE_NAME. " +
                        "Add SERVICE_NAME to docker-compose.yaml.")
    service_name = argv[1]
    if service_name not in variables_per_service:
        exit_with_error(f"Unknown service '{service_name}'. "
                        + f"Add the service to {os.path.basename(__file__)}.")


def exit_with_error(error: str):
    print(error)
    sys.exit(1)


def read_all_env_lines() -> list[str]:
    lines: list[str] = []
    with open(".env.postgres", 'r') as f:
        lines += f.readlines()
    with open(".env", 'r') as f:
        lines += f.readlines()
    return [line if line.endswith("\n") else f"{line}\n" for line in lines]


def filter_env_lines(lines: list[str]) -> list[str]:
    filtered_lines = []
    for line in lines:
        if line.strip() == "": # Empty lines are allowed.
            continue
        parts = line.split("=")
        if len(parts) != 2:
            exit_with_error(f"Invalid line: {line}.")
        variable_name = parts[0]
        if is_unknown_variable_name(variable_name):
            exit_with_error(f"Unknown env variable '{variable_name}'. "
                            + f"Add the variable to {os.path.basename(__file__)}.")
        if need_save_variable(variable_name):
            filtered_lines.append(line)
    return filtered_lines


def is_unknown_variable_name(variable_name: str) -> bool:
    possible_variable_names = {
        variable_name
        for service, variable_names in variables_per_service.items()
        for variable_name in variable_names
    }
    return variable_name not in possible_variable_names


def need_save_variable(variable_name: str) -> bool:
    return variable_name in variables_per_service[get_service_name()]


def get_service_name() -> str:
    return argv[1]


def save_env(lines: list[str]):
    with open(".env", 'w') as f:
        f.writelines(lines)


def remove_unused_files():
    os.remove(".env.postgres")


if __name__ == "__main__":
    shrink_env()
