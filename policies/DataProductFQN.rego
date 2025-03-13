package dataproduct

default allow := false
default warning := false

allow := true {
    startswith(input.afterState.dataProductVersion.info.fullyQualifiedName, "urn")
}