"use strict"

module.exports = (callback, context) => {
    callback(null, {"message": "You said: " + context})
}
