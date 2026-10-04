"""Report exporter with quadratic string concatenation in hot loop."""

def export_audit_log(records: list[dict], output_file: str) -> int:
    """Exports audit logs to disk.
    
    PERFORMANCE DEFECT:
    1. Quadratic string concatenation: `csv_body += line` in a loop of 100,000 items creates a new string object
       every iteration, resulting in O(N^2) allocations and GC pressure.
    2. Repeated unbuffered disk write on every iteration instead of batched or streamed writing.
    """
    csv_body = "timestamp,user,action,status\n"
    for record in records:
        line = f"{record['ts']},{record['user']},{record['action']},{record['status']}\n"
        csv_body += line
        
        # Flushes individual lines to disk repeatedly
        with open(output_file, "a") as f:
            f.write(line)
            
    return len(csv_body)
