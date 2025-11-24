# 🎢 OS-Project — Amusement Park Simulation

## 📘 Overview
This project simulates the operations of an amusement park using **Python threads** and **object-oriented programming**.  
Each visitor, ride, and staff member runs concurrently to model realistic park activity — queues, attractions, food stalls, and maintenance events.

---

## 🏗️ Project Structure


OS-PROJECT/
│
├── Config/
│ └── park.yaml
│
├── results/
│ └── (simulation metrics or CSV outputs)
│
├── source/
│ ├── core.py
│ ├── main.py
│ ├── metrics_recorder.py
│ │
│ ├── facilities/
│ │ ├── food.py
│ │ ├── queues.py
│ │ └── ride.py
│ │
│ ├── park/
│ │ ├── arrival.py
│ │ ├── maintenance.py
│ │ └── park.py
│ │
│ ├── staff/
│ │ └── base.py
│ │
│ └── visitors/
│ └── base.py
│
└── tests/
└── (unit or integration tests)


---

## 📂 Folder and File Descriptions

### 🧩 `Config/`
- **park.yaml**  
  Defines park configuration: opening hours, ride list, capacities, arrival rates, maintenance parameters, etc.  
  Editable to run different simulation scenarios without touching the code.

---

### 📊 `results/`
- Stores generated output data:
  - CSV metrics (`metrics.csv`)
  - Log files
  - Any additional simulation results or visualizations.

---

### ⚙️ `source/`
All main source code lives here.

#### **core.py**
- Contains the base utilities used everywhere:
  - `Clock` — controls simulated time and speed factor.
  - `Ids` — generates unique IDs for rides, staff, and visitors.
  - `Status` and `TicketType` enums.
  - Helper functions for randomness and weighted choices.

#### **main.py**
- Entry point of the simulation.
- Loads configuration, initializes all park components, starts threads (rides, visitors, maintenance), and coordinates simulation shutdown.
- Collects metrics at the end of a run.

#### **metrics_recorder.py**
- Central place to record data during the simulation:
  - Visitor arrivals, queue times, ride utilization, abandon rates, etc.
- Writes the final metrics to the `results/` folder for analysis.

---

### 🎡 `source/facilities/`
Handles all the **physical parts of the park** (rides, food areas, queues).

- **ride.py** — Defines the `Ride` class as a thread.  
  Manages boarding, running cycles, and notifying visitors when done.

- **queues.py** — Thread-safe queue logic for rides or food stalls.  
  Handles both regular and priority queues, as well as patience and abandonment.

- **food.py** — Defines Base Food Facility class and then instances of said class like Burger Truck and Ice Cream Stand.  
  Simulates ordering, cook time, food service and visitor waiting times/service times.

---

### 🏞️ `source/park/`
Coordinates the overall park behavior.

- **park.py** — Central park controller: manages rides, routes visitors, tracks availability.
- **arrival.py** — Generates new visitor threads over time, following the schedule from `park.yaml`.
- **maintenance.py** — Simulates random ride breakdowns and repairs, updating ride statuses.

---

### 👷 `source/staff/`
- **base.py** — Base class for park staff (e.g., ride operators or restaurant workers).  
  Defines basic thread logic, breaks, and task loops.

---

### 👨‍👩‍👧 `source/visitors/`
- **base.py** — Contains all visitor classes:
  - `Visitor` (base class)
  - `Child`, `Tourist`, `AdrenalineAddict`, etc.  
  Each type has different patience, preferences, and behaviors in queues and rides.

---

### 🧪 `tests/`
- Placeholder for future unit tests.
- You can add tests for queue behavior, ride capacity, or visitor routing logic.

---

## 🚀 Running the Simulation

1. Install dependencies (if any):
   ```bash
   pip install -r requirements.txt
