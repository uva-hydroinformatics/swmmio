#PARCEL FLOOD DAMAGE CALCULATIONS
#ASSUMES INPUT DATA IN ADDITION TO SWMM results


import pandas as pd

def flood_duration(node_flood_df, parcel_node_join_table, threshold=0.08333):

    """
    Given a dataframe with node flood duration and a csv table resulting
    from a one-to-many join of model shed drainage areas to parcels, this
    function returns a dataframe with flood data associated to each node.

    Assumptions:
        Flooding that occurs at any node in the SWMM model is applied to all
        parcels falling within that node's drainage area. Drainage areas are
        assumed to be generated using a Thiessen polygon method, or similar.
    """

    #read the one-to-many parcels to nodes table into a Dataframe
    raw_parcels = pd.read_csv(parcel_node_join_table)
    useful_cols = ['PARCELID', 'OUTLET', 'SUBCATCH', 'ADDRESS', 'REGULATOR']
    raw_parcels = raw_parcels[useful_cols]

    #clean up the nodes df, using only a few columns
    useful_cols = ['HoursFlooded', 'TotalFloodVol', 'MaxHGL', 'MaxNodeDepth']
    node_flood_df = node_flood_df[useful_cols]

    #join flood data to parcels by outlet, clean a bit more of the cols
    parcel_flood = pd.merge(raw_parcels, node_flood_df,
                            left_on='OUTLET', right_index=True)
    parcel_flood = parcel_flood[['PARCELID','HoursFlooded','TotalFloodVol']]

    #groupby parcel id to aggregate the duplicates, return the max of all dups
    parcel_flood_max = parcel_flood.groupby('PARCELID').max()

    #filter only parcels with flood duration above the threshold
    parcel_flood_max = parcel_flood_max.loc[parcel_flood_max.HoursFlooded>=threshold]
    return parcel_flood_max

def compare_flood_duration(basedf,altdf,threshold=0.08333,delta_threshold=0.25):

    df = basedf.join(altdf, lsuffix='Baseline', rsuffix='Proposed', how='outer')
    df = df.fillna(0) #any NaN means no flooding observed
    delta = df.HoursFloodedProposed - df.HoursFloodedBaseline
    df = df.assign(DeltaHours=delta)

    def categorize(parcel):

        if (parcel.HoursFloodedBaseline
            and parcel.HoursFloodedProposed >= delta_threshold):
            #parcel still floods, check how it changed:
            if parcel.DeltaHours > delta_threshold:
                #flooding duration increased (more than delta_threhold)
                return 'increased_flooding'

            elif parcel.DeltaHours < -delta_threshold:
                #flooding duration decreased (more than delta_threhold)
                return 'decreased_flooding'

        elif (parcel.HoursFloodedBaseline < delta_threshold
              and parcel.HoursFloodedProposed >= delta_threshold
              and abs(parcel.DeltaHours) >= delta_threshold):
            #flooding occurs where it perviously did not
            return 'new_flooding'

        elif (parcel.HoursFloodedBaseline >= threshold
              and parcel.HoursFloodedProposed < threshold
              and abs(parcel.DeltaHours) >= delta_threshold):
            #parcel that previously flooded no longer does
            return 'eliminated_flooding'

    cats = df.apply(lambda row: categorize(row), axis=1)
    df = df.assign(Category=cats)

    return df
