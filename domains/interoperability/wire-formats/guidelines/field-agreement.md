# Field agreement — two sides, one name, one nullability

Audit the mapping between what a producer writes and what a consumer reads. Mismatches here are silent, and the consumer's behaviour on absence is the usual place they hide.

## What to look for

- **Name mismatch on read:** A consumer reading `userId` from a payload the producer wrote as `user_id`, or a case difference, or a field nested one level deeper on one side, so the value is always absent and the consumer proceeds with a default.
- **Null conflated with absent:** A producer sending `null` for a field the consumer treats as "not provided", or omitting a field the consumer reads as `null`, so "cleared" and "never set" are the same value to one side and different to the other.
- **Default drift:** A field with a default in the schema, present in one component's code and absent in another's, so the same empty payload produces different values.
- **Required mismatch:** A field the producer considers optional and the consumer treats as required, so a legitimate record is rejected intermittently depending on which producer wrote it.
- **Absent consumed as zero or false:** A missing numeric or boolean field read through a coercion that turns absence into `0` or `false`, indistinguishable from a real zero.
- **Type widened on one side:** An integer sent where the consumer expects a string, or a string sent where a number is expected, accepted by a loose parser on one side and coerced differently by the other.
- **Enum value outside the consumer's set:** A producer emitting a value the consumer's closed enumeration does not contain, with the consumer's fallback silently selecting a default branch.
- **Key computed differently:** A dictionary key, cache key, or partition key built from a field the two sides format differently, so entries land under different keys and a lookup always misses.
