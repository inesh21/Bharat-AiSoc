package com.offlinecrop.assistant.engine

import com.offlinecrop.assistant.engine.executorch.parseActionChoice
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AdvisoryChoiceTest {
    @Test
    fun acceptsOnlyAListedActionIndex() {
        assertEquals(1, parseActionChoice("""{ "action": 1 } <|eot_id|>""", 2))
        for (output in listOf(
            """{"action":2}""",
            """{"action":-1}""",
            """{"action":"0"}""",
            """{"action":0,"action":1}""",
            """{"action":0,"dose":"1 mL"}""",
            """{"action":0} Extra treatment text""",
        )) {
            assertNull(output, parseActionChoice(output, 2))
        }
    }
}
