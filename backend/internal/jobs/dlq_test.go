// ----- DLQ tests @ backend/internal/jobs/dlq_test.go -----
package jobs

import (
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/stretchr/testify/assert"
)

func TestPushToDLQ(t *testing.T) {
	mr := miniredis.RunT(t)

	oldRdb := rdb
	t.Cleanup(func() { rdb = oldRdb })
	setTestRedis(mr.Addr())

	PushToDLQ("job-123", "crawl_sitemap", map[string]interface{}{"url": "test"}, "fetch failed", 3)

	count, err := GetDLQCount()
	assert.NoError(t, err)
	assert.Equal(t, int64(1), count)
}

func TestPopDLQEntries(t *testing.T) {
	mr := miniredis.RunT(t)

	oldRdb := rdb
	t.Cleanup(func() { rdb = oldRdb })
	setTestRedis(mr.Addr())

	PushToDLQ("job-1", "task", map[string]interface{}{}, "err1", 1)
	PushToDLQ("job-2", "task", map[string]interface{}{}, "err2", 2)

	entries := PopDLQEntries(0)
	assert.Len(t, entries, 2)
	assert.Equal(t, "job-1", entries[0].JobID)
	assert.Equal(t, "job-2", entries[1].JobID)

	count, _ := GetDLQCount()
	assert.Equal(t, int64(0), count)
}

func TestPopDLQEntriesEmpty(t *testing.T) {
	mr := miniredis.RunT(t)

	oldRdb := rdb
	t.Cleanup(func() { rdb = oldRdb })
	setTestRedis(mr.Addr())

	entries := PopDLQEntries(0)
	assert.Empty(t, entries)
}
