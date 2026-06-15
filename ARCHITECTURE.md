# SpatialScrap Architecture & Development Roadmap

## Current State (v0.1.0)

SpatialScrap is a **local, manual Python CLI tool and Gradio web interface** for mesh decimation and relief shadow baking.

### What It Is:
- ✅ **Local CLI tool**: Run from terminal with file arguments
- ✅ **Gradio web UI**: Browser-based interface for manual file processing
- ✅ **Standalone library**: Can be imported as `spatial_scrap.processor`
- ✅ **Blender integration**: Optional relief shadow baking via Blender API

### What It Is NOT (Yet):
- ❌ **Networked**: No API endpoints or server architecture
- ❌ **Automated**: Requires manual file uploads and button clicks
- ❌ **XR-integrated**: Cannot receive requests from Android XR headsets
- ❌ **Headless**: Requires user interaction

---

## Planned: Edge-Server API Pipeline (Milestone 1 - Grant Funded)

The next phase transforms SpatialScrap into a **networked, headless edge-server pipeline**:

### What Will Be Built:
- 🔲 **REST API server** wrapping the core processor
- 🔲 **Headless processing**: Background job queue for batch operations
- 🔲 **XR client integration**: Accept file requests from Android spatial computing devices
- 🔲 **Automatic response delivery**: Stream optimized .glb files back to client
- 🔲 **Docker containerization**: Portable, reproducible deployment

### Architecture (Proposed):
```
Android XR Client
    ↓
REST API Server (Flask/FastAPI)
    ↓
Job Queue (Redis/Celery)
    ↓
SpatialScrapProcessor (existing)
    ↓
Blender (headless mode)
    ↓
Optimized .glb
    ↓
Response Stream → XR Client
```

---

## Why the Distinction Matters

This GitHub repo documents the **research and math** (v0.1.0). The **grant funds the infrastructure** (Milestone 1) that makes it production-ready for spatial computing deployment.

---

## Contributing

Currently, improvements should focus on:
1. Core decimation and baking quality
2. Mesh format support (currently: OBJ, STL, PLY, EXR, PNG)
3. Blender integration robustness
4. CLI/UI usability

The API architecture will be implemented in Milestone 1 as a separate deployment layer on top of this library.

For questions, see `README.md` or open an issue.
