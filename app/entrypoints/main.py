from app.core.config import get_settings
from app.workflows.healthcare_graph import build_workflow


def main() -> None:
    settings = get_settings()
    workflow = build_workflow(settings)

    initial_state = {"question": "What are early symptoms of type 2 diabetes?", "context": "", "answer": ""}
    for update in workflow.stream(initial_state):
        print(update)

    print("Final answer:", workflow.invoke(initial_state)["answer"])


if __name__ == "__main__":
    main()
