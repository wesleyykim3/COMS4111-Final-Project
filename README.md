# Migraine Tracker - COMS 4111 Project Part 3

## Team Information
- Poonnakarn Panjasriprakarn (pp2965)
- Wesley Kim (wk2430)

## Database Information
**PostgreSQL Account:** pp2965

This is the same database that we used for Part 2. Please check this database for our project submission.

## Application URL
**http://34.75.108.30:8111**


## Implementation Status

### Core Features Implemented

**1. Episode Management (Fully Implemented)**
- Complete CRUD operations for migraine episodes
- Episodes track: start time, end time, intensity (1-10 scale), attack type, menstrual cycle correlation, and notes
- List view with detailed episode pages
- Form-based creation and editing with validation

**2. Multi-Relationship Tracking (Fully Implemented)**
- Episodes can be associated with multiple medications, symptoms, triggers, and pain locations
- Multi-select interface allows users to choose from existing reference data
- All many-to-many relationships properly managed through junction tables (`episode_pain_locations`, `episode_symptoms`, `episode_triggers`, `episode_medications`)
- Relationships displayed with color-coded badges on detail pages

**3. Reference Data Management (Fully Implemented)**
- Complete CRUD operations for all reference entities:
  - Medications (generic name, dosage in milligrams, route)
  - Symptoms
  - Triggers
  - Pain locations
  - Attack types
- Users can add, edit, and delete custom entries
- Dedicated management pages accessible via dropdown navigation menu

**4. Basic Statistics Dashboard (Implemented)**
- Home page displays three key metrics:
  - Total episodes count
  - Episodes this month
  - Average pain intensity
- Real-time database queries using PostgreSQL aggregation functions

**5. User Interface (Implemented)**
- Clean, modern design using Tailwind CSS
- Responsive layout works on desktop and mobile
- Intuitive navigation with header links and dropdown menus
- Color-coded badges for different data types (medications in blue, symptoms in red, triggers in yellow, pain locations in green)

### Features Simplified or Deferred

The following features from the original proposal were simplified or deferred to future development:

1. **User Registration System**: The application currently uses a default user (user_id = 1) rather than implementing full user authentication and registration with demographic details.

2. **Calendar Interface**: Episodes are displayed in a list view sorted by date rather than a visual calendar interface.

3. **Advanced Dashboard Analytics**: The dashboard shows basic statistics rather than the full range of proposed analytics (monthly migraine days vs. headache days, min/max severity, medication usage days, visual charts/graphs).

4. **Medication Trade Names**: Only generic medication names are tracked. The `medications_trade` table from the original schema was not implemented.

---

## Interesting Database Operations

### Page 1: Episode Creation with Relationships (`/episodes/new`)

**Purpose:**  
This page allows users to create a new migraine episode and simultaneously associate it with multiple medications, symptoms, triggers, and pain locations in a single form submission.

**How It Works:**

When the page loads, it performs 5 separate queries to populate the multi-select dropdowns:
```sql
SELECT id, name FROM pp2965.attack_types ORDER BY name
SELECT id, name FROM pp2965.pain_locations ORDER BY name
SELECT id, name FROM pp2965.symptoms ORDER BY name
SELECT id, name FROM pp2965.triggers ORDER BY name
SELECT id, generic_name, milligrams FROM pp2965.medications ORDER BY generic_name
```

When the user submits the form, the application performs a complex multi-table insertion within a single transaction:

1. **Insert the main episode record:**
```sql
INSERT INTO pp2965.episodes 
(user_id, start_time, end_time, intensity, attack_type_id, had_menses, notes, created_at)
VALUES (:user_id, :start_time, :end_time, :intensity, :attack_type_id, :had_menses, :notes, NOW())
RETURNING id;
```

2. **Insert into junction tables** (one INSERT per selected item):
```sql
-- For each selected pain location
INSERT INTO pp2965.episode_pain_locations (episode_id, pain_location_id)
VALUES (:episode_id, :location_id);

-- For each selected symptom
INSERT INTO pp2965.episode_symptoms (episode_id, symptom_id)
VALUES (:episode_id, :symptom_id);

-- For each selected trigger
INSERT INTO pp2965.episode_triggers (episode_id, trigger_id)
VALUES (:episode_id, :trigger_id);

-- For each selected medication
INSERT INTO pp2965.episode_medications (episode_id, medication_id)
VALUES (:episode_id, :medication_id);
```

3. **Commit the transaction**

**Why This Is Interesting:**

1. **Transaction Atomicity:** All insertions happen within a single database transaction. If any part fails (e.g., foreign key violation), the entire operation rolls back automatically. This ensures we never have orphaned records or partial episode data.

2. **Many-to-Many Complexity:** A single user action (submitting one form) results in coordinated writes across 5 different tables. The user might select 2 pain locations, 3 symptoms, 1 trigger, and 2 medications, resulting in 1 episode record + 8 junction table records, all properly linked through foreign keys.

---

### Page 2: Episode Detail View (`/episodes/<id>`)

**Purpose:**  
This page displays complete information about a single episode by reconstructing data from across the entire normalized database schema.

**How It Works:**

The page performs 6 separate queries to gather all related information:

1. **Main episode data:**
```sql
SELECT id, user_id, start_time, end_time, intensity, attack_type_id, 
       had_menses, notes, created_at
FROM pp2965.episodes
WHERE id = :id;
```

2. **Attack type name (if exists):**
```sql
SELECT name 
FROM pp2965.attack_types 
WHERE id = :attack_type_id;
```

3. **Associated pain locations:**
```sql
SELECT pl.name 
FROM pp2965.pain_locations pl
JOIN pp2965.episode_pain_locations epl ON pl.id = epl.pain_location_id
WHERE epl.episode_id = :id
ORDER BY pl.name;
```

4. **Associated symptoms:**
```sql
SELECT s.name 
FROM pp2965.symptoms s
JOIN pp2965.episode_symptoms es ON s.id = es.symptom_id
WHERE es.episode_id = :id
ORDER BY s.name;
```

5. **Associated triggers:**
```sql
SELECT t.name 
FROM pp2965.triggers t
JOIN pp2965.episode_triggers et ON t.id = et.trigger_id
WHERE et.episode_id = :id
ORDER BY t.name;
```

6. **Associated medications with dosage:**
```sql
SELECT m.generic_name, m.milligrams
FROM pp2965.medications m
JOIN pp2965.episode_medications em ON m.id = em.medication_id
WHERE em.episode_id = :id
ORDER BY m.generic_name;
```

**Why This Is Interesting:**

1. **Query Strategy:** We use 6 separate queries instead of one massive multi-way JOIN. This approach avoids Cartesian products that would result from joining multiple many-to-many relationships simultaneously. For example, if an episode has 3 medications and 4 symptoms, a single JOIN would produce 12 rows that need deduplication. Our approach is more efficient and avoids this issue.

2. **Handling Optional Relationships:** Each JOIN query properly handles cases where no relationships exist. If an episode has no associated medications, the query returns an empty result set, which the template displays as "None recorded" rather than breaking or showing confusing empty space.
