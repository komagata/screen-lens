// Keep in sync with translation_settings.default_target; only supported codes leave here.
function target(lcAll, lcMessages, lang) {
  var value = lcAll || lcMessages || lang || "C"
  var parts = value.split(".")[0].split("@")[0].toLowerCase().replace(/_/g, "-").split("-")
  if (["ja", "en", "es", "fr"].indexOf(parts[0]) !== -1) return parts[0]
  if (parts[0] === "zh" && !parts.some(function(p) { return ["hant", "tw", "hk", "mo"].indexOf(p) !== -1 })) return "zh-CN"
  return "en"
}
