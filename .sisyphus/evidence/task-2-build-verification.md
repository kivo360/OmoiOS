# Task 2 Evidence: egress-proxy Build & Snapshot Integration

## 1. Cross-compile produces linux/amd64 binary

```
$ GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o egress-proxy .
```

Result: success (no output).

## 2. Binary verified as ELF x86-64 static

```
$ file egress-proxy/egress-proxy
egress-proxy/egress-proxy: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, ...
```

## 3. Snapshot script stages the binary

```
$ grep -n "omoios-egress-proxy" scripts/build_omo_snapshot.py
115:        .add_local_file(str(REPO / "egress-proxy" / "egress-proxy"), "/usr/local/bin/omoios-egress-proxy")
116:        .run_commands("sudo chmod +x /usr/local/bin/omoios-egress-proxy")
```

## 4. Go tests pass

```
$ cd egress-proxy && go test ./...
ok  	github.com/kivo360/omoios/egress-proxy	(cached)
```
