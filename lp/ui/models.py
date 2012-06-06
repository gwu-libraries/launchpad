from django.db import models

class BibMfhd(models.Model):
    bib_id = models.IntegerField(primary_key=True)
    mfhd_id = models.IntegerField()

    class Meta:
        db_table = 'bib_mfhd'
        managed = False

class BibIndex(models.Model):
    bib_id = models.IntegerField(primary_key=True)
    index_code = models.CharField(max_length=4)
    normal_heading = models.TextField(max_length=150)
    display_heading = models.TextField(max_length=150)

    class Meta:
        db_table = 'bib_index'
        managed = False

class BibMaster(models.Model):
    bib_id = models.IntegerField(primary_key=True, db_column='bib_id')
    library = models.ForeignKey('Library')
    suppress_in_opac = models.CharField(max_length=1)
    create_date = models.DateTimeField()
    update_date = models.DateTimeField()
    export_ok = models.CharField(max_length=1)
    export_ok_date = models.DateTimeField()
    export_ok_opid = models.TextField(max_length=10)
    export_ok_location_id = models.IntegerField()
    export_date = models.DateTimeField()
    exists_in_dps = models.CharField(max_length=1, null=False)
    exists_in_dps_date = models.DateTimeField()

    class Meta:
        db_table = 'bib_master'
        managed = False

class BibText(models.Model):
    bib_id = models.IntegerField(primary_key=True, db_column='bib_id')
    author = models.TextField(max_length=255)
    title = models.TextField(max_length=255)
    title_brief = models.TextField(max_length=150)
    uniform_title = models.TextField(max_length=255)
    edition = models.TextField(max_length=100)
    isbn = models.TextField(max_length=50)
    issn = models.TextField(max_length=20)
    lccn = models.TextField(max_length=20)
    network_number = models.TextField(max_length=30)
    series = models.TextField(max_length=255)
    coden = models.TextField(max_length=6)
    gponum = models.TextField(max_length=20)
    stdtech = models.TextField(max_length=30)
    other_std_num = models.TextField(max_length=30)
    begin_pub_date = models.TextField(max_length=4)
    end_pub_date = models.TextField(max_length=4)
    pub_dates_combined = models.TextField(max_length=9)
    pub_place = models.TextField(max_length=100)
    publisher = models.TextField(max_length=150)
    publisher_number = models.TextField(max_length=40)
    imprint = models.TextField(max_length=200)
    language = models.TextField(max_length=3)
    bib_format = models.TextField(max_length=2)
    record_status = models.TextField(max_length=1)
    encoding_level = models.TextField(max_length=1)
    descrip_form = models.TextField(max_length=1)
    field_008 = models.TextField(max_length=40)
    place_code = models.TextField(max_length=3)
    date_type_status = models.CharField(max_length=1)
    map_projection = models.CharField(max_length=2)
    map_math_data = models.TextField(max_length=255)
    stock_number = models.TextField(max_length=50)

    class Meta:
        db_table = 'bib_text'
        managed = False

class Item(models.Model):
    item_id = models.IntegerField(primary_key=True, db_column='item_id')
    perm_location = models.IntegerField()
    temp_location = models.IntegerField()
    item_type_id = models.IntegerField()
    temp_item_type_id = models.IntegerField()
    copy_number = models.IntegerField()
    on_reserve = models.CharField(max_length=1)
    reserve_charges = models.IntegerField()
    pieces = models.IntegerField()
    price = models.IntegerField()
    spine_label = models.TextField(max_length=25)
    historical_charges = models.IntegerField()
    historical_browses = models.IntegerField()
    recalls_placed = models.IntegerField()
    holds_placed = models.IntegerField()
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField()
    create_operator_id = models.TextField(max_length=10)
    modify_operator_id = models.TextField(max_length=10)
    create_location_id = models.IntegerField()
    modify_location_id = models.IntegerField()
    item_sequence_number = models.IntegerField()
    historical_bookings = models.IntegerField()
    media_type_id = models.IntegerField()
    short_loan_charges = models.IntegerField()
    magnetic_media = models.CharField(max_length=1)
    sensitize = models.CharField(max_length=1)

    class Meta:
        db_table = 'item'
        managed = False

class ItemStatus(models.Model):
    item_id = models.IntegerField(primary_key=True, db_column='item_id')
    item_status = models.IntegerField()
    item_status_date = models.DateTimeField()

    class Meta:
        db_table = 'item_status'
        managed = False

class ItemStatusType(models.Model):
    item_status_type = models.IntegerField(primary_key=True)
    item_status_desc = models.TextField(max_length=25, null=False)

    class Meta:
        db_table = 'item_status_type'
        managed = False

class Library(models.Model):
    library_id = models.IntegerField(primary_key=True)
    library_name = models.TextField(max_length=50)
    library_display_name = models.TextField(max_length=80)
    nuc_code = models.TextField(max_length=15)

    class Meta:
        db_table = 'library'
        managed = False

class Location(models.Model):
    location_id = models.IntegerField(primary_key=True, db_column='location_id')
    location_code = models.TextField(max_length=10)
    location_name = models.TextField(max_length=25)
    location_display_name = models.TextField(max_length=60)
    location_spine_label = models.TextField(max_length=25)
    location_opac = models.CharField(max_length=1)
    suppress_in_opac = models.CharField(max_length=1)
    library_id = models.IntegerField()
    mfhd_count = models.IntegerField()

    class Meta:
        db_table = 'location'
        managed = False

class MfhdMaster(models.Model):
    mfhd_id = models.IntegerField(primary_key=True, db_column='mfhd_id')
    location_id = models.IntegerField()
    call_no_type = models.CharField(max_length=1)
    normalized_call_no = models.TextField(max_length=300)
    display_call_no = models.TextField(max_length=300)
    suppress_in_opac = models.CharField(max_length=1)
    source_module = models.CharField(max_length=1)
    record_status = models.CharField(max_length=1)
    record_type = models.CharField(max_length=1)
    encoding_level = models.CharField(max_length=1)
    field_007 = models.TextField(max_length=23)
    field_008 = models.TextField(max_length=32)
    create_date = models.DateTimeField()
    update_date = models.DateTimeField()
    export_ok = models.CharField(max_length=1)
    export_ok_date = models.DateTimeField()
    export_ok_opid = models.TextField(max_length=10)
    export_ok_location_id = models.IntegerField()
    export_date = models.DateTimeField()

    class Meta:
        db_table = 'mfhd_master'
        managed = False

