class FixTag:
    # --- Administrative / Session Tags ---
    BEGIN_STRING       = 8   # (e.g., FIX.4.4)
    BODY_LENGTH        = 9   
    MSG_TYPE           = 35  # (e.g., A=Logon, 0=Heartbeat)
    SENDER_COMP_ID     = 49  
    TARGET_COMP_ID     = 56  
    MSG_SEQ_NUM        = 34  
    SENDING_TIME       = 52  
    CHECKSUM           = 10  
    
    # --- Logon / Logout Specific ---
    ENCRYPT_METHOD     = 98  
    HEARTBT_INT        = 108 
    RESET_SEQ_NUM_FLAG = 141 
    USERNAME           = 553 
    PASSWORD           = 554 

    # --- Sequence Reset & Resend ---
    BEGIN_SEQ_NO       = 7
    END_SEQ_NO         = 16
    NEW_SEQ_NO         = 36
    GAP_FILL_FLAG      = 123
    POSS_DUP_FLAG      = 43 

    # --- Common Application Tags (New Order Single) ---
    CL_ORD_ID          = 11  # Client Order ID
    SYMBOL             = 55  # e.g., AAPL
    SIDE               = 54  # 1=Buy, 2=Sell
    TRANSACT_TIME      = 60  
    ORDER_QTY          = 38  
    ORD_TYPE           = 40  # 1=Market, 2=Limit
    PRICE              = 44  
    HANDL_INST         = 21  # 1=Private, 2=Public, 3=Manual
    TIME_IN_FORCE      = 59  # 0=Day, 1=GTC

    # --- Execution Report Tags ---
    ORDER_ID           = 37  # Exchange Order ID
    EXEC_ID            = 17  
    ORD_STATUS         = 39  # 0=New, 1=Partially Filled, 2=Filled 


class FixMsgType:
    HEARTBEAT        = "0"
    TEST_REQUEST     = "1"
    RESEND_REQUEST   = "2"
    REJECT           = "3"
    SEQUENCE_RESET   = "4"
    LOGOUT           = "5"
    EXECUTION_REPORT = "8"
    LOGON            = "A"
    NEW_ORDER_SINGLE = "D"