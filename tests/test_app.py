import copy

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities

# Snapshot initial state once at import time so every test can reset to it
INITIAL_ACTIVITIES = copy.deepcopy(activities)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Restore the in-memory activities dict to its original state after every test."""
    yield
    activities.clear()
    activities.update(copy.deepcopy(INITIAL_ACTIVITIES))


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_root_redirects_to_index():
    # Arrange — no setup needed; default app state is sufficient

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# ---------------------------------------------------------------------------
# GET /activities
# ---------------------------------------------------------------------------

def test_get_activities_returns_200():
    # Arrange — no setup needed

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200


def test_get_activities_returns_all_activities():
    # Arrange
    expected_activities = list(INITIAL_ACTIVITIES.keys())

    # Act
    response = client.get("/activities")
    data = response.json()

    # Assert
    assert list(data.keys()) == expected_activities


def test_get_activities_items_have_required_keys():
    # Arrange
    required_keys = {"description", "schedule", "max_participants", "participants"}

    # Act
    response = client.get("/activities")
    data = response.json()

    # Assert
    for name, details in data.items():
        assert required_keys <= details.keys(), f"Activity '{name}' is missing required keys"


# ---------------------------------------------------------------------------
# POST /activities/{activity_name}/signup
# ---------------------------------------------------------------------------

def test_signup_adds_participant():
    # Arrange
    activity_name = "Chess Club"
    new_email = "newstudent@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={new_email}")

    # Assert
    assert response.status_code == 200
    assert new_email in activities[activity_name]["participants"]
    assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"


def test_signup_unknown_activity_returns_404():
    # Arrange
    unknown_activity = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = client.post(f"/activities/{unknown_activity}/signup?email={email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_duplicate_email_returns_400():
    # Arrange
    activity_name = "Chess Club"
    existing_email = activities[activity_name]["participants"][0]

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email={existing_email}")

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up"


def test_signup_full_activity_returns_400():
    # Arrange — fill Chess Club (max 12) to capacity with unique emails
    activity_name = "Chess Club"
    activity = activities[activity_name]
    while len(activity["participants"]) < activity["max_participants"]:
        filler_email = f"filler{len(activity['participants'])}@mergington.edu"
        activity["participants"].append(filler_email)

    # Act
    response = client.post(f"/activities/{activity_name}/signup?email=overflow@mergington.edu")

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"


# ---------------------------------------------------------------------------
# DELETE /activities/{activity_name}/participants/{email}
# ---------------------------------------------------------------------------

def test_unregister_removes_participant():
    # Arrange
    activity_name = "Chess Club"
    email_to_remove = activities[activity_name]["participants"][0]

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{email_to_remove}")

    # Assert
    assert response.status_code == 200
    assert email_to_remove not in activities[activity_name]["participants"]
    assert response.json()["message"] == f"Unregistered {email_to_remove} from {activity_name}"


def test_unregister_unknown_activity_returns_404():
    # Arrange
    unknown_activity = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = client.delete(f"/activities/{unknown_activity}/participants/{email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_unknown_participant_returns_404():
    # Arrange
    activity_name = "Chess Club"
    unknown_email = "notregistered@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity_name}/participants/{unknown_email}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found in this activity"
