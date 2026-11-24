import csv
import io
from fastapi import HTTPException, Response


def safe(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def export(item):
    if not item.result:
        raise HTTPException(409, '估算结果尚未完成')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['补巡单', '状态', '结论'])
    writer.writerow([safe(item.title), item.status, safe(item.result['summary'])])
    for key, value in item.result['metrics'].items():
        writer.writerow([key, value])
    rows = item.result['rows']
    if rows:
        writer.writerow([])
        columns = ['区段', 'A 轮', 'B 轮', '重合', '合并实见', '估计总量', '估计漏查', '估计方差', '建议']
        writer.writerow(columns)
        writer.writerows([safe(row[key]) for key in columns] for row in rows)
    return Response(content='\ufeff' + stream.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="bench-plan-{item.id}.csv"'})
