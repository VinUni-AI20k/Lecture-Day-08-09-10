# Day09 - Phân công 5 thành viên (không conflict khi merge)

## Mục tiêu
- Mỗi người có một cụm file riêng, làm độc lập trên branch riêng.
- Merge không conflict theo nguyên tắc: không sửa file thuộc owner khác.
- Nam chỉ làm tester + docs, ít code, mức dễ nhất.

## Nguyên tắc làm việc
1. Mỗi nhánh chỉ được sửa file trong phạm vi đã phân công.
2. Nếu cần sửa file của người khác, tạo issue và đợi người đó merge xong rồi mới rebase.
3. Trước khi mở PR: rebase vào main mới nhất và chạy test local.
4. Không commit file tạm, không commit thay đổi ngoài phạm vi.

## Phân công theo người (owner file rõ ràng)

| Thành viên | Branch đề xuất | File được sửa (độc quyền) | Công việc chính | Độ khó |
|---|---|---|---|---|
| Tú Anh | feature/day09-tuanh-graph-routing | day09/lab/graph.py; day09/lab/contracts/worker_contracts.yaml | Hoàn thiện supervisor route, bỏ placeholder, nối worker thật vào graph, chốt schema state/contract | Vừa |
| Dũng | feature/day09-dung-retrieval-mcp | day09/lab/workers/retrieval.py; day09/lab/mcp_server.py | Hoàn thiện retrieval worker + search_kb/get_ticket_info/check_access_permission/create_ticket trong MCP | Vừa |
| Được | feature/day09-duoc-policy-worker | day09/lab/workers/policy_tool.py; day09/lab/data/test_questions.json | Hoàn thiện policy exception, MCP call flow trong policy worker, bổ sung test case policy/multi-hop | Vừa |
| Thành | feature/day09-thanh-synthesis-eval | day09/lab/workers/synthesis.py; day09/lab/eval_trace.py | Hoàn thiện synthesis grounded + confidence; hoàn thiện compare_single_vs_multi và report eval | Vừa |
| Nam | chore/day09-nam-docs-testing | day09/lab/docs/system_architecture.md; day09/lab/docs/routing_decisions.md; day09/lab/docs/single_vs_multi_comparison.md; day09/lab/reports/group_report.md | Tester + docs: chạy lệnh, tổng hợp số liệu, điền template docs, không sửa file .py | Dễ (siêu dễ) |

## Việc cụ thể cho Nam (tester/docs, ít code)
1. Không sửa bất kỳ file .py nào.
2. Sau khi 4 bạn còn lại merge xong, chạy các lệnh:
   - python day09/lab/graph.py
   - python day09/lab/eval_trace.py
   - python day09/lab/eval_trace.py --analyze
   - python day09/lab/eval_trace.py --compare
3. Ghi kết quả vào 3 file docs:
   - docs/system_architecture.md
   - docs/routing_decisions.md
   - docs/single_vs_multi_comparison.md
4. Cập nhật reports/group_report.md bằng số liệu thực tế.

## Thứ tự merge để tránh conflict
1. Merge nhánh của Tú Anh trước (graph + contract).
2. Sau đó Dũng, Được, Thành làm song song trên branch riêng, base từ main mới nhất.
3. Merge lần lượt: Dũng -> Được -> Thành (mỗi PR rebase vào main trước khi merge).
4. Nam merge cuối cùng (chỉ docs/report), base từ main đã ổn định.

## Checklist trước khi mở PR
- Branch đúng tên và đúng scope.
- Chỉ thay đổi file thuộc owner.
- Chạy test liên quan:
  - Tú Anh: python day09/lab/graph.py
  - Dũng: python day09/lab/workers/retrieval.py và python day09/lab/mcp_server.py
  - Được: python day09/lab/workers/policy_tool.py
  - Thành: python day09/lab/workers/synthesis.py và python day09/lab/eval_trace.py --analyze
  - Nam: python day09/lab/eval_trace.py --compare
- Mô tả PR phải có: file đã sửa, kết quả test, phạm vi thay đổi.

## Rule chốt để không conflict
- Một file chỉ có một owner chính.
- Docs do Nam owner, code do 4 bạn còn lại owner.
- Bắt buộc rebase main trước merge.
