# Persona Sets Storage Locations

## Overview

Persona sets are stored in two places:
1. **Database (PostgreSQL)**: Loaded persona sets and their data
2. **File System**: JSON source files for default persona sets

## 1. Database Storage (PostgreSQL)

### Location
Persona sets are stored in a **PostgreSQL database** specified by your `DATABASE_URL` environment variable.

### Database Tables

#### `persona_sets` Table
Stores persona set metadata:
- `id` (Integer, Primary Key): Unique identifier
- `name` (String): Persona set name
- `description` (Text): Description of the set
- `rqe_scores` (JSON): Diversity scores
- `diversity_score` (JSON): Diversity metrics
- `validation_scores` (JSON): Validation scores
- `generation_cycle` (Integer): Generation cycle number
- `status` (String): Status (generated, expanded, validated)
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

#### `personas` Table
Stores individual personas within sets:
- `id` (Integer, Primary Key): Unique identifier
- `persona_set_id` (Integer, Foreign Key): Links to `persona_sets.id`
- `name` (String): Persona name
- `persona_data` (JSON): Full persona data (all fields)
- `image_url` (String): URL/path to persona image
- `image_prompt` (Text): Prompt used to generate image
- `similarity_score` (JSON): Validation similarity scores
- `validation_status` (String): Validation status
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime): Last update timestamp

### Database Connection

The database connection is configured via `DATABASE_URL` in your `.env` file:

```bash
DATABASE_URL=postgresql://pep_user:pep_password@localhost:5432/pep_db
```

### Docker Volume

When using Docker Compose, the database data is stored in a Docker volume:
- **Volume Name**: `postgres_data`
- **Container Path**: `/var/lib/postgresql/data`
- **Host Path**: Managed by Docker (typically in Docker's volume directory)

To find the actual location:
```bash
docker volume inspect pep-be_postgres_data
```

### Accessing the Database

**Local Development:**
```bash
psql -h localhost -U pep_user -d pep_db
```

**Docker:**
```bash
docker exec -it pep_postgres psql -U pep_user -d pep_db
```

**View Persona Sets:**
```sql
SELECT id, name, description, created_at FROM persona_sets;
```

**View Personas:**
```sql
SELECT id, persona_set_id, name, created_at FROM personas;
```

## 2. File System Storage (JSON Source Files)

### Default Locations

The system searches for persona set JSON files in these locations (in order):

#### Local Development
1. **Project Root**: `{project_root}/default_personas*.json`
   - Example: `/Users/danialamin/Documents/GitHub/pep-be/default_personas.json`
   - Example: `/Users/danialamin/Documents/GitHub/pep-be/default_personas_set1.json`

2. **Current Working Directory**: `./default_personas*.json`
   - Wherever you run the application from

3. **Directory Structure**: `{project_root}/default_personas/*.json`
   - Example: `/Users/danialamin/Documents/GitHub/pep-be/default_personas/set1.json`

#### Docker Container
1. **Container Root**: `/app/default_personas*.json`
   - Example: `/app/default_personas.json`
   - Example: `/app/default_personas_set1.json`

2. **Directory Structure**: `/app/default_personas/*.json`
   - Example: `/app/default_personas/set1.json`

### File Naming Patterns

The system recognizes these file patterns:

| Pattern | Example | Set Name |
|---------|---------|----------|
| `default_personas.json` | `default_personas.json` | "default" |
| `default_personas_{name}.json` | `default_personas_set1.json` | "set1" |
| `default_personas/{name}.json` | `default_personas/research.json` | "research" |

### Docker Volume Mounts

In `docker-compose.yml`, the project root is mounted to `/app`:
```yaml
volumes:
  - ./app:/app/app
  - ./uploads:/app/uploads
  - ./static:/app/static
```

**Note**: The `default_personas*.json` files in the project root are accessible in the container at `/app/default_personas*.json` because the entire project directory is available.

### Recommended File Organization

**Option 1: Root Directory (Current)**
```
pep-be/
├── default_personas.json
├── default_personas_set1.json
├── default_personas_set2.json
└── default_personas_research.json
```

**Option 2: Directory Structure (Recommended for Many Sets)**
```
pep-be/
├── default_personas/
│   ├── set1.json
│   ├── set2.json
│   ├── research.json
│   └── marketing.json
└── default_personas.json  # Default/fallback
```

## 3. Image Storage

Persona images are stored separately:

### Location
- **Local**: `/app/static/images/personas/` (in container)
- **Host**: `./static/images/personas/` (mounted volume)
- **URL Path**: `/static/images/personas/persona_{id}.png`

### Docker Volume
Mounted in `docker-compose.yml`:
```yaml
volumes:
  - ./static:/app/static
```

## 4. Data Flow

### Loading Process

1. **Source**: JSON file on file system
   - Location: Project root or `/app/` in container
   - Format: JSON with `personas` array and `metadata` object

2. **Processing**: System reads JSON file
   - Function: `load_default_personas()` in `app/utils/load_default_personas.py`
   - Searches multiple locations until file is found

3. **Storage**: Data written to PostgreSQL
   - Creates `PersonaSet` record in `persona_sets` table
   - Creates `Persona` records in `personas` table
   - Each persona's full data stored in `persona_data` JSON column

### Retrieval Process

1. **API Request**: `GET /api/v1/personas/sets`
2. **Database Query**: Reads from `persona_sets` and `personas` tables
3. **Response**: Returns JSON with all persona sets and their personas

## 5. Backup and Migration

### Backing Up Persona Sets

**Database Backup:**
```bash
# Export all persona sets
pg_dump -h localhost -U pep_user -d pep_db -t persona_sets -t personas > persona_sets_backup.sql
```

**JSON Files Backup:**
```bash
# Copy JSON files
cp default_personas*.json /backup/location/
# Or entire directory
cp -r default_personas/ /backup/location/
```

### Exporting Persona Sets to JSON

Use the download endpoint:
```bash
GET /api/v1/personas/{persona_set_id}/download
```

Returns JSON file with complete persona set data.

## 6. Environment-Specific Storage

### Development (Local)
- **Database**: Local PostgreSQL instance
- **JSON Files**: Project root directory
- **Images**: `./static/images/personas/`

### Production (Docker)
- **Database**: PostgreSQL container with persistent volume
- **JSON Files**: `/app/` in container (from project root)
- **Images**: `/app/static/images/personas/` (mounted volume)

### Production (Cloud)
- **Database**: Managed PostgreSQL service (e.g., AWS RDS, Google Cloud SQL)
- **JSON Files**: Can be stored in:
  - Container filesystem (ephemeral)
  - Object storage (S3, GCS) - requires code changes
  - Version control (Git) - recommended
- **Images**: Object storage (S3, GCS) or CDN

## 7. Finding Your Storage Locations

### Check Database Location
```bash
# View DATABASE_URL
echo $DATABASE_URL

# Or check .env file
cat .env | grep DATABASE_URL
```

### Check JSON File Locations
```bash
# List available persona set files
GET /api/v1/personas/available-persona-sets

# Or manually check
ls -la default_personas*.json
ls -la default_personas/
```

### Check Docker Volumes
```bash
# List volumes
docker volume ls

# Inspect volume location
docker volume inspect pep-be_postgres_data
```

## 8. Important Notes

### Persistence

✅ **Database**: Persists across container restarts (Docker volume)  
✅ **JSON Files**: Persist if in mounted volume or project directory  
⚠️ **Container Filesystem**: Ephemeral - data lost on container removal

### Recommendations

1. **JSON Files**: Keep in version control (Git)
2. **Database**: Use persistent volumes in production
3. **Images**: Use object storage for production scalability
4. **Backups**: Regular database backups recommended
5. **Version Control**: Track JSON file changes in Git

### File Permissions

Ensure the application has read access to JSON files:
```bash
chmod 644 default_personas*.json
```

And write access to image directory:
```bash
chmod 755 static/images/personas/
```
