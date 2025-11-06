# Migraine Tracker - COMS 4111 Project Part 3

## Team Information
- Poonnakarn Panjasriprakarn (pp2965)
- Wesley Kim (wk2430)

## Database Information
**PostgreSQL Account:** pp2965

This is the same database that we used for Part 2. Please check this database for our project submission.

## Application URL
**http://34.75.108.30:8111**

Note: Our VM will remain running to ensure this URL continues to work for evaluation.

## Implementation Status

### Features from Part 1 Proposal

All proposed features from Part 1 have been fully implemented:

**1. Episode Management**
- Users can create, view, edit, and delete migraine episodes
- Episodes track start time, end time, intensity (1-10 scale), notes, and menstrual cycle correlation
- Implemented as proposed with full CRUD functionality

**2. Multi-Relationship Tracking**
- Episodes can be associated with multiple medications, symptoms, triggers, and pain locations
- Users select from existing reference data when creating/editing episodes
- All many-to-many relationships properly managed through junction tables
- Implemented exactly as proposed

**3. Reference Data Management**
- Complete CRUD operations for medications, symptoms, triggers, pain locations, and attack types
- Users can add custom entries to track their specific experiences
- Implemented as proposed with dedicated management pages for each entity type

**4. Statistics Dashboard**
- Home page displays key metrics: total episodes, episodes this month, and average intensity
- Provides quick overview of episode patterns
- Implemented as proposed with real-time database queries

**5. User Interface**
- Modern, responsive design using Tailwind CSS
- Intuitive navigation with dropdown menus
- Color-coded visual indicators for different data types
- Exceeded original proposal with enhanced UX features


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
