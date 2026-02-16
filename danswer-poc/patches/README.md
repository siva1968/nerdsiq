# Onyx Logout Fix Patches

This directory contains git patches for fixing the logout bug in Onyx v2.11.0.

## Patches Included

### 1. logout-route-fix.patch
**File:** `web/src/app/auth/logout/route.ts`  
**Issue:** Cookie deletion was restricted to cloud instances only  
**Fix:** Changed `if (NEXT_PUBLIC_CLOUD_ENABLED)` to `if (true)` to force cookie deletion on all instances

### 2. userss-header-filter-fix.patch  
**File:** `web/src/lib/userSS.ts`  
**Issue:** Invalid connection headers from nginx proxy caused undici fetch errors  
**Fix:** Added header filtering to remove `Connection` and `Upgrade` headers before making internal API calls

## How to Apply

### Automated Build (Recommended)
```bash
cd /home/prasad/Documents/dev/NERDSIQ/nerdsiq/danswer-poc
./build-custom-web.sh
```

### Manual Application
```bash
# Clone Onyx source
git clone --depth 1 --branch v2.11.0 https://github.com/onyx-dot-app/onyx.git onyx-source
cd onyx-source

# Apply patches
git apply ../danswer-poc/patches/logout-route-fix.patch
git apply ../danswer-poc/patches/userss-header-filter-fix.patch

# Build custom image
cd web
sudo docker build -t onyx-web-custom:logout-fix .
```

## Verification

After building and deploying:
```bash
# Should return 401 (not 500)
curl -X POST http://localhost:3100/auth/logout

# Check logs - should have no "TypeError: fetch failed"
sudo docker logs onyx-web --tail 50 | grep -i error
```

## Upstream Status

These patches address a known issue in Onyx v2.11.0:
- **GitHub Issue:** #3763 "Logout doesn't work"
- **Root Cause:** Self-hosted instances don't clear cookies + nginx proxy headers cause fetch errors
- **Status:** Not yet fixed in official release

Monitor https://github.com/onyx-dot-app/onyx/releases for official fix.

## Related Documentation
- [LOGOUT_FIX_SUMMARY.md](../LOGOUT_FIX_SUMMARY.md) - Complete technical documentation
- [build-custom-web.sh](../build-custom-web.sh) - Automated build script
- [docker-compose-onyx.yml](../docker-compose-onyx.yml) - Uses custom image
