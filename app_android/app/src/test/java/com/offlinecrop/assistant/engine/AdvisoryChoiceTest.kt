package com.offlinecrop.assistant.engine

import com.offlinecrop.assistant.engine.executorch.parseActionChoice
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AdvisoryChoiceTest {
    @Test
    fun acceptsOnlyAListedActionIndex() {
        assertEquals(1, parseActionChoice(" 1 ", 2))
        for (output in listOf(
            "2",
            "01",
            "0 Treatment text",
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
